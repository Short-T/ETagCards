# server_connector.py
# Author: Taylor Short
# Clean, safe HTTP-only connector for the card game server

import requests
import json
import re
import time

BASE_URL = "http://localhost:9900"
POLL_INTERVAL = 5


# ------------------------------------------------------------
# UNIVERSAL SAFE PARSER
# ------------------------------------------------------------
def safe_parse_response(response):
    """
    Accepts ANY server response and returns a clean Python dict.
    Repairs invalid JSON, strips single quotes, fixes keys, etc.
    Always returns a dict with at least:
        { "type": "...", "message": "...", "data": ... }
    """
    text = response.text.strip()

    # Try direct JSON first
    try:
        return json.loads(text)
    except:
        pass

    # Attempt to repair common Node mistakes
    repaired = text

    # Replace single quotes with double quotes
    repaired = repaired.replace("'", '"')

    # Add quotes around unquoted keys: type: -> "type":
    repaired = re.sub(r'(\w+):', r'"\1":', repaired)

    # Remove trailing commas
    repaired = re.sub(r',\s*}', '}', repaired)
    repaired = re.sub(r',\s*]', ']', repaired)

    # Try parsing again
    try:
        return json.loads(repaired)
    except:
        # Final fallback
        return {
            "type": "error",
            "message": "Invalid server response",
            "raw": text
        }


# ------------------------------------------------------------
# USER FUNCTIONS
# ------------------------------------------------------------
def create_user(username, name):
    params = {"username": username, "name": name}
    r = requests.get(f"{BASE_URL}/users/create", params=params)
    return safe_parse_response(r)


def login_user(username):
    params = {"username": username}
    r = requests.get(f"{BASE_URL}/users/login", params=params)
    data = safe_parse_response(r)

    if data.get("type") == "success":
        id = data.get("data", {})
        return id.get("userId", 0)

    print("Login error:", data)
    return 100


def get_user_list():
    r = requests.get(f"{BASE_URL}/users")
    data = safe_parse_response(r)

    if data.get("type") == "success":
        return data.get("data", [])

    return []


def get_user_id_from_username(username):
    users = get_user_list()
    for u in users:
        if u["username"].lower() == username.lower():
            return u["userId"]
    return None


# ------------------------------------------------------------
# SESSION FUNCTIONS
# ------------------------------------------------------------
def get_session_requests(user_id):
    params = {"userId": user_id}
    r = requests.get(f"{BASE_URL}/sessions/requests/user", params=params)
    data = safe_parse_response(r)

    if data.get("type") != "success":
        return []

    raw = data.get("data", [])
    return raw if isinstance(raw, list) else [raw]


def accept_session(user_id, contact_id):
    params = {"userId": user_id, "contactId": contact_id}
    r = requests.get(f"{BASE_URL}/sessions/requests/accept", params=params)
    data = safe_parse_response(r)

    return data.get("type") == "success"


def initiate_session(user_id, contact_id):
    params = {"userId": user_id, "contactId": contact_id}
    r = requests.get(f"{BASE_URL}/sessions/requests/add", params=params)
    data = safe_parse_response(r)

    return data.get("type") == "success"


# ------------------------------------------------------------
# GAME STATE FUNCTIONS
# ------------------------------------------------------------
def encode_selected_cards(cards):
    return ",".join(str(c) for c in cards) if cards else ""


def decode_selected_cards(card_string):
    if not card_string:
        return []
    return [int(x) for x in card_string.split(",") if x.isdigit()]


def get_state(user_id, contact_id):
    params = {"userId": user_id, "contactId": contact_id}
    r = requests.get(f"{BASE_URL}/vumark/data/get", params=params)
    data = safe_parse_response(r)

    if data.get("type") != "success":
        return None

    raw = data.get("data", {})

    return {
        "selected_cards": decode_selected_cards(raw.get("selected_cards", "")),
        "discard_card_id": int(raw.get("discard_card_id", 0)),
        "restart_flag": int(raw.get("restart_flag", 0)),
        "sender_cards": int(raw.get("sender_cards", 0)),
        "receiver_cards": int(raw.get("receiver_cards", 0)),
        "sender_id": int(raw.get("sender_id", 0)),
        "receiver_id": int(raw.get("receiver_id", 0)),
    }


def update_state(user_id, contact_id, selected_cards, discard_card_id,
                 restart_flag, user_cards, receiver_cards=0):

    params = {
        "userId": user_id,
        "contactId": contact_id,
        "selectedCards": f"\"{encode_selected_cards(selected_cards)}\"",
        "discardCardId": discard_card_id,
        "restart_flag": restart_flag,
        "userCards": user_cards,
        "receiverCards": receiver_cards
    }

    r = requests.get(f"{BASE_URL}/vumark/data/update", params=params)
    data = safe_parse_response(r)

    if "restart game" in r.text.lower():
        return "restart"

    return "ok"


def update_cards_and_discard(state, selected_cards, discard_card):
    return update_state(
        state.user_id,
        state.contact_id,
        selected_cards=selected_cards,
        discard_card_id=discard_card,
        restart_flag=0,
        user_cards=len(selected_cards)
    )


def get_opponent_card_count(state, user_id):
    if not state:
        return 0

    if user_id == state["receiver_id"]:
        return state["sender_cards"]
    else:
        return state["receiver_cards"]


def is_restart_requested(state, user_id):
    if not state:
        return False

    flag = state["restart_flag"]
    return flag != 0 and flag != user_id