# game_state.py
#
# Centralized container for all game-related state.
# This replaces globals and makes the main script far easier to manage.
#
# Phases:
#   "lobby"  – user login, session creation, waiting for opponent
#   "setup"  – first NFC tap selects the discard label
#   "game"   – main gameplay loop
#
# The GameState object is intentionally lightweight and holds only data.
# All logic lives in main.py or helper modules.

class GameState:
    def __init__(self):
        # -----------------------------
        # High-level phase control
        # -----------------------------
        self.phase = "init"   # lobby → setup → game

        # -----------------------------
        # User / session info
        # -----------------------------
        self.user_id = None
        self.player_name = None
        self.contact_id = None
        self.contact_name = None

        # -----------------------------
        # Physical table state
        # -----------------------------
        self.discard_mac = None      # MAC address of discard ESL
        self.your_macs = []          # MACs for your 5 active card slots
        self.extra_macs = []         # MACs for the 4 extra slots

        # -----------------------------
        # Card + deck state
        # -----------------------------
        self.your_cards = []         # Your current 5 card indices
        self.remaining_cards = []    # Remaining deck after drawing
        self.discard_card_index = 0  # Current discard card index

        # -----------------------------
        # Online sync state
        # -----------------------------
        self.selected_card_indices = []  # All card indices used so far
        self.opponent_card_count = 0     # Opponent's remaining cards
        self.opponent_restart = False    # Opponent requested restart

        # -----------------------------
        # Event queue
        # -----------------------------
        # NFC events:   ("nfc", mac)
        # Input events: ("input", text)
        self.event_queue = None

        # -----------------------------
        # Flags and misc
        # -----------------------------
        self.restart_requested = False

    # Optional helper if you want to keep main.py clean
    def set_phase(self, new_phase):
        print(f"[GameState] Transition: {self.phase} → {new_phase}")
        self.phase = new_phase
