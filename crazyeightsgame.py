# Important note for this file
# your_cards are pulling the template name
# player_cards are pulling the template id
# for rendering

import queue
import threading
import random
import argparse
import re
import time
import sys

from server_api import api
import server_connector
from ascii_cards import print_hand
from nfc_connector import NFCReader

discard_mac = ""
discard_id = "BLANK"
state_flag = ""
PLAYER_CARDS = ["E1000001CFB7", "E1000001CF41", "E1000001CF73",
                "E1000001CF66", "E1000001CF43", "E1000001CEFC",
                "E1000001CF00", "E1000001CEF9", "E1000001CEFD"]
update_event_queue = queue.Queue()
UID_TO_MAC = {
    "02F3005CC2B466": "E1000001CF43",
    "02F3005CC0CA08": "E1000001CFB7",
    "02F3005CBE7955": "E1000001CF66",
    "02F3005CC107C7": "E1000001CEFC",
    "02F3005CBC8D74": "E1000001CF4A",
    "02F3005CC1B6F1": "E1000001CF00",
    "02F3005CBE4B15": "E1000001CF41",
    "02F3005CC24532": "E1000001CF3F",
    "02F3005CBE1BCE": "E1000001CF45",
    "02F3005CC2A5A5": "E1000001CEFD"
    "02F3005CBE3937": "E1000001CF73",
    "02F3005CC22594": "E1000001CEF9"
}



def input_listener():
    while True:
        user_input = input("Enter template name to bind to discard: ").strip()
        update_event_queue.put(user_input)

def on_connect_callback(tag):
    global state_flag, discard_mac, PLAYER_CARDS
    uid = tag.identifier.hex().upper()
    print(f"on_connect_callback : {state_flag} : Tag detected, UID={uid}")
    
    # Pull Mac address from NDEF record
    mac_address = extract_mac_from_tag(tag)
    if not mac_address:
        mac_address = UID_TO_MAC.get(uid)
    print(f"on_connect_callback : {state_flag} : data : {mac_address}")
    
    if not mac_address:
        print("MAC address failed to extract - have to retry the tap")
    else:
        # Switch for game state_flag
        print(f"MAC={mac_address} STATE={state_flag}")
        
        # We cache the mac address for the next update
        UID_TO_MAC[uid] = mac_address
        
        if state_flag == "init":
            wait()
            return False
        elif state_flag == "setup":
            discard_mac = mac_address
            if mac_address in PLAYER_CARDS:
                PLAYER_CARDS.remove(mac_address)
            print(f"Updating discard mac address : {mac_address}")
        elif state_flag == "game":
            if mac_address == discard_mac:
                print("Discard display detected, no need to do anything")
            else:
                # Here we do a discard interaction and update the display
                update_event_queue.put(mac_address)
                print("Discarding")
        else:
            if mac_address == discard_mac:
                print("Discard display detected, no need to do anything")
            else:
                # Here we do a discard interaction and update the display
                update_event_queue.put(mac_address)
                print(f"callback on {mac_address}, sending update to discard mac") 
    wait()
    return False

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

def main():
    global state_flag, discard_mac, PLAYER_CARDS
    state_flag = "init"
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["online", "offline"])
    args = parser.parse_args()

    api.connect() # Minew api wrapper handles displays
    print("Connected to Minew API")

    templates = api.get_template_list()
    print(f"Templates:, {[t[1] for t in templates]}")

    # Initialize the NFC
    reader = NFCReader()
    reader.start(on_connect_callback)
    
    wait()
    
    # STATE ONE : LOG IN USER 
    #
    name = input("Enter your display name: ")
    if args.mode == "online":
        created = server_connector.create_user(name, name) # Try to create the user first 
        user_id = server_connector.login_user(name) #login user
        # LOGGED IN
        server_connector.get_user_list()
        print(f"Starting session polling for user ID: {user_id}")
        # Thread for input listener
        threading.Thread(target=input_listener,
                        args=(update_event_queue,),
                        daemon=True).start()
        print("Input listener thread started")
        server_connector.lobby_mode(user_id, input_queue)
    
    state_flag = "setup"
     # A session is connected between two players
    
    # The rest is performed until keyboard interrupt
    try:
        # Keep main alive until Ctrl+C
        print("\nTap a card to set it as the discard pile. Press Ctrl+C to quit.")
        while state_flag == "setup":
            if discard_mac != "":
                print("Discard MAC detected, switching to GAME state")
                state_flag = "game"
            else:
                time.sleep(0.1)   # prevent CPU spin
        
        # State flag in game mode now
        # Start the game, shuffle cards, display discard
        # This is the starting game state
        random.shuffle(templates)
        discard_id = templates[0][0]
        your_cards = [t[1] for t in templates[1:6]]
        player_cards = [p[0] for p in templates[6:11]]
        remaining_cards = templates[11:]
        discarded_macs = []
        
        # Print your cards on the console
        print(f"Discard card: {templates[0][1]}")
        print(f"Your cards:")
        print_hand([t[1] for t in templates[1:6]])
        print(f"Templates: [t[1] for t in templates[1:6]]")
        
        # Display player cards on the ESL
        api.update_device_binding(discard_mac, discard_id)
        for mac, template_id in zip(PLAYER_CARDS, player_cards):
            api.update_device_binding(mac, template_id)

        # API calls to display discard and distribute cards
        while state_flag == "game":
            try:
                event = update_event_queue.get_nowait()
                # Event is a MAC address if it was initiated by an NFC connection
                # Event is a Template name if initiated by console input
                print(event)
                if event in PLAYER_CARDS:
                    if not event in discarded_macs:
                        #NFC was tapped, transfer the card
                        print(f"NFC Input* Discard display updated to template from '{event}'")
                        discarded_macs.append(event)
                        player_cards.pop(0)
                        api.transferCards(event, discard_mac)
                    else:
                        print("Processing previous discard interaction")
                else:
                    #Manual user input, update the discard display
                    print(f"Manual Input* Discard display updated to template '{event}'")
                    if event in (t[1] for t in templates):
                        api.update_device_binding(discard_mac, next((t[0] for t in templates if t[1] == user_input), None))
                        your_cards.pop(0)
                        print_hand(f"your_cards")
                        print(f"Templates: [t[1] for t in templates[1:6]]")
            except queue.Empty:
                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nShutting down readers…")
        api.save_and_close()
        reader.stop()
        print("All readers closed. Program end")


if __name__ == "__main__":
    main()
