# ascii_cards.py
# Used to render cards in ascii on the console terminal

SUIT_MAP = {
    "H": "♥",
    "D": "♦",
    "C": "♣",
    "S": "♠"
}

CARD_TEMPLATE = [
    "┌─────────┐",
    "│{r:<2}       │",
    "│         │",
    "│    {s}    │",
    "│         │",
    "│       {r:>2}│",
    "└─────────┘"
]

def parse_card(card_str):
    # Example: "52_3.5_S_5"
    _, _, suit, rank = card_str.split("_")
    return rank, SUIT_MAP[suit]

def render_card(rank, suit):
    return [line.format(r=rank, s=suit) for line in CARD_TEMPLATE]

def print_hand(card_strings):
    cards = [parse_card(c) for c in card_strings]
    rendered = [render_card(r, s) for r, s in cards]
    for row in zip(*rendered):
        print("  ".join(row))
