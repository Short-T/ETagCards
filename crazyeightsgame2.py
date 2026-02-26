# Online only version of tangible cards
# Connects with app version of game

import queue
import threading
import random
import argparse
import re
import time
import sys

from server_api import api
from game_state import GameState
import server_connector
import card_deck
from ascii_cards import print_hand
from nfc_connector import NFCReader

discard_id = 0
PLAYER_CARDS = ["E1000001CFB7", "E1000001CF41", "E1000001CF73",
                "E1000001CF66", "E1000001CF43", "E1000001CEFC",
                "E1000001CF00", "E1000001CEF9", "E1000001CEFD"]
UID_TO_MAC = {}



def extract_mac_from_tag(tag):
    if not tag.ndef:
        return None

    for record in tag.ndef.records:
        # Decode safely
        try:
            data = record.data.decode('ascii', errors='ignore')
        except:
            continue

        # 1. Your original format: mac=XXXXXXXXXXXX
        m = re.search(r'mac=([A-Fa-f0-9]{12})', data)
        if m:
            return m.group(1)

        # 2. Minew URI formats
        m = re.search(r'([A-Fa-f0-9]{12})', data)
        if m:
            return m.group(1)

        # 3. Raw hex payload
        if len(data) >= 12 and all(c in "0123456789ABCDEFabcdef" for c in data.strip()):
            return data.strip()[:12]

    return None

def wait(seconds=1):
    for _ in range(int(seconds * 4)):   # 4 updates per second
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(0.25)
    print()  # newline after loader
    
def run_enter_name(state):
    print("\n=== ENTER DISPLAY NAME ===")
    print("Type your display name and press Enter.")

    while state.phase == "init":
        try:
            event_type, value = state.event_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        if event_type != "input":
            if event_type == "nfc":
                #Assign discard card
                state.discard_mac = value
                continue
            else:
                continue

        name = value.strip()
        if not name:
            print("Name cannot be empty. Try again.")
            continue

        state.player_name = name
        server_connector.create_user(name, name)
        state.user_id = server_connector.login_user(name)

        print(f"Logged in as {name}, user_id={state.user_id}")
        print("List of users:")
        print(server_connector.get_user_list())

        state.phase = "lobby"
        return

def run_lobby(state, api):
    print("\n=== LOBBY ===")
    print("Type a username or user ID to start a session.")
    print("Waiting for incoming requests...")

    while state.phase == "lobby":
        try:
            event_type, value = state.event_queue.get(timeout=0.1)
        except queue.Empty:
            # Poll for incoming session requests
            requests = server_connector.get_session_requests(state.user_id)
            pending = [r for r in requests if r.get("is_accepted") == 0]

            if pending:
                contact_id = pending[0]["user_id"]
                print(f"Incoming session request from {contact_id}...")
                if server_connector.accept_session(state.user_id, contact_id):
                    print(f"Accepted session from {contact_id}")
                    state.contact_id = contact_id
                    state.phase = "game"
                    return
            continue

        if event_type != "input":
            continue

        user_input = value.strip()
        if not user_input:
            continue

        # Numeric → treat as user ID
        if user_input.isdigit():
            contact_id = int(user_input)
            print(f"Attempting to start session with user ID {contact_id}...")
            if server_connector.initiate_session(state.user_id, contact_id):
                print(f"Session started with user {contact_id}")
                state.contact_id = contact_id
                state.phase = "game"
                return
            else:
                print("Failed to start session. Try again.")
                continue

        # Otherwise treat as username
        username = user_input
        print(f"Looking up username '{username}'...")
        contact_id = server_connector.get_user_id_from_username(username)

        if contact_id is None:
            print(f"No user found with username '{username}'. Try again.")
            continue

        print(f"Found user '{username}' (ID {contact_id}). Attempting session...")
        if server_connector.initiate_session(state.user_id, contact_id):
            print(f"Session started with {username} (ID {contact_id})")
            state.contact_id = contact_id
            state.phase = "game"
            return
        else:
            print("Failed to start session. Try again.")

def run_game(state, api):
    print("\n=== GAME PHASE ===")
    # Handle the main game loop and polling for event updates
    
    server_state = server_connector.get_state(state.user_id, state.contact_id)
    if not server_state:
        discard_id = 0
        cards_in_use = []
    else:
        discard_id = server_state.get("discard_card_id", 0)
        cards_in_use = server_state.get("selected_cards", [])
    
    deck = [i for i in range(1, 53) if i not in cards_in_use]
    random.shuffle(deck)
    
    # Update discard display
    if discard_id == 0:
        discard_id = deck.pop(0)
    state.discard_card_index = discard_id
    api.update_device_binding(state.discard_mac, card_deck.CARD_INDEX_TO_TEMPLATE_ID[discard_id])

    # Update card hand displays
    available_macs = [m for m in PLAYER_CARDS if m != state.discard_mac]
    state.your_macs = []
    state.your_cards = []
    state.remaining_cards = deck
    for mac in available_macs[:5]:
        if not state.remaining_cards:
            break
        card = state.remaining_cards.pop(0)
        state.your_macs.append(mac)
        state.your_cards.append(card)
        api.update_device_binding(mac, card_deck.CARD_INDEX_TO_TEMPLATE_ID[card])

    # Update server with initial game state
    server_connector.update_state(
        state.user_id,
        state.contact_id,
        selected_cards=state.your_cards,
        discard_card_id=discard_id,
        restart_flag=0,
        user_cards=len(state.your_cards)
    )
    
    print("Game starting...")
    state.phase == "game"
    last_poll = time.time()
    POLL_INTERVAL = 0.5

    while state.phase == "game":
        now = time.time()
        
        # We poll during the game phase to check for new discards
        if now - last_poll >= POLL_INTERVAL:
            last_poll = now
            # poll server here
            server_state = server_connector.get_state(state.user_id, state.contact_id)
            if server_state:
                dis = server_state.get("discard_card_id", 0)

                if dis != state.discard_card_index:
                    print(f"Opponent discarded card index {dis}")
                    if dis == -1:
                        # Show blank discard or placeholder
                        api.update_device_binding(
                            state.discard_mac,
                            card_deck.DISCARD_TEMPLATE_ID
                        )
                        continue
                    state.discard_card_index = dis
                    api.update_device_binding(
                        state.discard_mac,
                        card_deck.CARD_INDEX_TO_TEMPLATE_ID[dis]
                    )
        # Regardless of the status of new discards, we can check for an event
        try:
            event_type, mac = state.event_queue.get(timeout=0.1)       
            if event_type == "nfc":
                print(f"NFC event in game: {mac}")
                if mac not in state.your_macs:
                    # DRAW CARD HERE
                    if state.remaining_cards:
                        new_card = state.remaining_cards.pop(0)
                        print(f"Drawing card {new_card} onto {mac}")
                        state.your_cards.append(new_card)
                        state.your_macs.append(mac)
                        api.update_device_binding(mac, card_deck.CARD_INDEX_TO_TEMPLATE_ID[new_card])
                        # Sync the server with the new updates 
                        server_connector.update_state(
                            state.user_id,
                            state.contact_id,
                            selected_cards=state.your_cards,
                            discard_card_id=state.discard_card_index,
                            restart_flag=0,
                            user_cards=len(state.your_cards)
                        )
                    else:
                        print("No cards left in deck to draw.")
                        # reshuffle function here
                        continue
                else:
                    # Discard the tapped card
                    idx = state.your_macs.index(mac)
                    discarded_card = state.your_cards[idx]
                    print(f"Discarding card {discarded_card} from {mac}")
                    
                    # Remove from hand + Update discard
                    state.discard_card_index = discarded_card
                    api.update_device_binding(
                        state.discard_mac,
                        card_deck.CARD_INDEX_TO_TEMPLATE_ID[discarded_card]
                    )
                    
                    state.your_cards.pop(idx)
                    state.your_macs.pop(idx)
                    api.update_device_binding(mac, card_deck.DISCARD_TEMPLATE_ID)
                    # Sync the server with the new updates 
                    server_connector.update_state(
                        state.user_id,
                        state.contact_id,
                        selected_cards=state.your_cards,
                        discard_card_id=discarded_card,
                        restart_flag=0,
                        user_cards=len(state.your_cards)
                    )
        except queue.Empty:
            continue
        time.sleep(0.01)


def main():
    api.connect()  # Minew api
    print("Connected to Minew API")

    reader = NFCReader()  # NFC api
    reader.start(on_connect_callback)
    print("NFC reader started")
    
    try:
        while True:
            if state.phase == "init":
                run_enter_name(state)
            if state.phase == "lobby":
                run_lobby(state, api)
            elif state.phase == "game":
                run_game(state, api)
            else:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down readers…")
        api.save_and_close()
        reader.stop()
        print("All readers closed. Program end")


if __name__ == "__main__":
    state = GameState()
    state.event_queue = queue.Queue()

    # 2. Start input listener thread that feeds state.event_queue
    def input_listener(state):
        while True:
            try:
                user_input = input("> ").strip()
                state.event_queue.put(("input", user_input))
            except EOFError:
                continue
            except KeyboardInterrupt:
                print("Exiting input listener!")
                return
    threading.Thread(
        target=input_listener,
        args=(state,),
        daemon=True
    ).start()

    # 3. NFC callback
    def on_connect_callback(tag):
        try:
            uid = tag.identifier.hex().upper()
            mac_address = extract_mac_from_tag(tag)
            print(f"on_connect_callback : Tag detected, UID={uid}, MAC={mac_address}")

            if not mac_address:
                mac_address = UID_TO_MAC.get(uid)
            if not mac_address:
                print("Mac address failed to extract - repolling")
                return False  # Continue polling if mac extraction failed
            state.event_queue.put(("nfc", mac_address))
        except Exception as e:
            print(f"NFC callback error: {e}")
        return False
    # 4. Enter main phase loop
    main()