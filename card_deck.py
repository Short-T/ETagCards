# card_deck.py
#
# Defines the canonical 52‑card deck mapping for Tangible cards to integrate
# with digital and MR apps
# Provides mappings:
#   CARD_INDEX_TO_NAME
#   NAME_TO_TEMPLATE_ID
#   CARD_INDEX_TO_TEMPLATE_ID
#
# Also includes helpers:
#   load_template_mapping(api)
#   card_index_to_template(idx)
#   template_to_card_index(template_name)
#
# Discard template ID is included for index 0.

DISCARD_TEMPLATE_ID = "2020214213040934912"   # Tangible discard template


# ------------------------------------------------------------
# 1. Android Deck Definition (Indices 0–52)
# ------------------------------------------------------------

# Index 0 is the discard placeholder ("1D.png" in Android)
CARD_INDEX_TO_NAME = {0: "DISCARD"}

# Android rank/suit order
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["H", "S", "D", "C"]   # Hearts, Spades, Diamonds, Clubs

# Fill indices 1–52
idx = 1
for rank in RANKS:
    for suit in SUITS:
        CARD_INDEX_TO_NAME[idx] = f"{rank}{suit}"
        idx += 1


# ------------------------------------------------------------
# 2. Template Mapping (filled at runtime)
# ------------------------------------------------------------

NAME_TO_TEMPLATE_ID = {}
CARD_INDEX_TO_TEMPLATE_ID = {}


def load_template_mapping(api):
    """
    Load Minew template list and build NAME_TO_TEMPLATE_ID and CARD_INDEX_TO_TEMPLATE_ID.
    Must be called once after api.connect().
    """
    global NAME_TO_TEMPLATE_ID, CARD_INDEX_TO_TEMPLATE_ID

    NAME_TO_TEMPLATE_ID = {}
    CARD_INDEX_TO_TEMPLATE_ID = {}

    # Fetch Minew templates (demoId, demoName)
    templates = api.get_template_list("52")
    
    # Build name → templateId mapping
    for demoId, demoName in templates:
        NAME_TO_TEMPLATE_ID[demoName] = demoId
        print(f"{demoName} set as ID {demoId} in NAME_TO_TEMPLATE_ID")

    missing = []

    # Build index → templateId mapping for all 52 cards
    for idx, name in CARD_INDEX_TO_NAME.items():

        # Index 0 = discard placeholder
        if idx == 0:
            CARD_INDEX_TO_TEMPLATE_ID[idx] = DISCARD_TEMPLATE_ID
            continue

        # Expected Minew template name format: "52_3.5_X_Y>"
        rank = name[:-1]
        suit = name[-1]

        expected_name = f"52_3.5_{suit}_{rank}"

        if expected_name in NAME_TO_TEMPLATE_ID:
            CARD_INDEX_TO_TEMPLATE_ID[idx] = NAME_TO_TEMPLATE_ID[expected_name]
            print(f"{NAME_TO_TEMPLATE_ID[expected_name]} with name {expected_name} set as ID {idx} in CARD_INDEX_TO_TEMPLATE_ID")
        else:
            missing.append((idx, name, expected_name))

    # Report missing templates
    if missing:
        print("\n WARNING: Missing Minew templates for the following cards:")
        for idx, name, expected in missing:
            print(f"  - Card index {idx}: {name} (expected template '{expected}')")
        print("These cards will cause KeyErrors if drawn.\n")