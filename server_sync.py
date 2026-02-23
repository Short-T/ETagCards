# server_sync.py
#
# Handles communication with the Node.js server for online card sync.
# Mirrors the Android app's behavior exactly.
#
# Functions provided:
#   get_state(user_id, contact_id)
#   update_state(user_id, contact_id, selected_cards, discard_card_id,
#                restart_flag, user_cards, receiver_cards=0)
#   encode_selected_cards(list[int]) -> str
#   decode_selected_cards(str) -> list[int]
#   get_opponent_card_count(state, user_id)
#   is_restart_requested(state, user_id)
#
# Server expects:
#   selected_cards: "3,12,25"   (comma-separated ints)
#   discard_card_id: int
#   restart_flag: 0 or userId
#   userCards: int
#   receiverCards: int (Python always sends 0, Android fills its own)
#
# The server determines sender/receiver based on userId matching sender_id.

import requests
import json

SERVER_BASE = "http://<YOUR_SERVER_IP>:<PORT>"   # Fill this in


# ------------------------------------------------------------
# Encoding / Decoding Helpers
# ------------------------------------------------------------

def encode_selected_cards(cards):
    """Convert list[int] → comma-separated string."""
    if not cards:
        return ""
    return ",".join(str(c) for c in cards)


def decode_selected_cards(card_string):
    """Convert comma-separated string → list[int]."""
    if not card_string or card_string.strip() == "":
        return []
    return [int(x) for x in card_string.split(",") if x.isdigit()]


# ------------------------------------------------------------
# Server Calls
# ------------------------------------------------------------

def get_state(user_id, contact_id):
    """
    Mirrors Android's SERVER_VUMARK_DATA_GET.
    Returns a dict with:
        selected_cards: list[int]
        discard_card_id: int
        restart_flag: int
        sender_cards: int
        receiver_cards: int
        sender_id: int
        receiver_id: int
    """
    url = f"{SERVER_BASE}/vumark/data/get"
    params = {
        "userId": user_id,
        "contactId": contact_id
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()

        if data.get("type") != "success":
            return None

        raw = data["data"]
        raw_cards = raw.get("selected_cards", "")
        raw_cards = raw_cards.replace("\"", "")  # Android sends quoted lists

        return {
            "selected_cards": decode_selected_cards(raw_cards),
            "discard_card_id": int(raw.get("discard_card_id", 0)),
            "restart_flag": int(raw.get("restart_flag", 0)),
            "sender_cards": int(raw.get("sender_cards", 0)),
            "receiver_cards": int(raw.get("receiver_cards", 0)),
            "sender_id": int(raw.get("sender_id")),
            "receiver_id": int(raw.get("receiver_id"))
        }

    except Exception as e:
        print(f"[server_sync] Error in get_state: {e}")
        return None


def update_state(user_id, contact_id, selected_cards, discard_card_id,
                 restart_flag, user_cards, receiver_cards=0):
    """
    Mirrors Android's SERVER_VUMARK_DATA_UPDATE.
    Python always sends receiver_cards=0.
    """
    url = f"{SERVER_BASE}/vumark/data/update"

    params = {
        "userId": user_id,
        "contactId": contact_id,
        "selectedCards": encode_selected_cards(selected_cards),
        "discardCardId": discard_card_id,
        "restart_flag": restart_flag,
        "userCards": user_cards,
        "receiverCards": receiver_cards
    }

    try:
        r = requests.get(url, params=params)
        text = r.text.strip()

        # Android checks for "restart game"
        if "restart game" in text.lower():
            return "restart"

        return "ok"

    except Exception as e:
        print(f"[server_sync] Error in update_state: {e}")
        return "error"


# ------------------------------------------------------------
# Convenience Helpers
# ------------------------------------------------------------

def get_opponent_card_count(state, user_id):
    """Return how many cards the opponent has."""
    if not state:
        return 0

    if user_id == state["receiver_id"]:
        return state["sender_cards"]
    else:
        return state["receiver_cards"]


def is_restart_requested(state, user_id):
    """Return True if the opponent requested a restart."""
    if not state:
        return False

    flag = state["restart_flag"]
    return flag != 0 and flag != user_id