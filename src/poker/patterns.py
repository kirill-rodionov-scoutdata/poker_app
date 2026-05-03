from __future__ import annotations

import re

HAND_HEADER = re.compile(
    r"^(PokerStars Game #|PokerStars Hand #|Hand #)",
    re.MULTILINE,
)
GTO_HEADER = re.compile(r"PokerStars Game #(\d+):")
WPN_PS_HEADER = re.compile(r"PokerStars Hand #(\d+):")
WPN_HIS_HEADER = re.compile(r"^Hand #(\d+) -")

BUTTON_SEAT = re.compile(r"Seat #(\d+) is the button")
SEAT = re.compile(r"^Seat (\d+): (.+?) \(\$?([0-9.]+)")

STREET_HEADER = re.compile(
    r"^\*\*\* (HOLE CARDS|FLOP|TURN|RIVER|SHOW DOWN|SUMMARY) \*\*\*"
)
FLOP_CARDS = re.compile(r"^\*\*\* FLOP \*\*\* \[([^\]]+)\]")

ACTION_COLON = re.compile(
    r"^(.+?): (folds|checks|calls|bets|raises)"
    r"(?:\s+\$([0-9.]+))?(?:\s+to\s+\$([0-9.]+))?"
)
SUMMARY_POSITION = re.compile(
    r"^Seat \d+: (.+?) \((small blind|big blind|button)\)"
)
SKIP_LINE = re.compile(
    r"^(Main pot|Total pot|Uncalled bet|Dealt to|Board \[|Rake|"
    r".*collected|.*doesn't show|.*does not show|.*did not show|"
    r".*shows? \[|.*showed \[|.*wins?\b)"
)
ALL_IN_SUFFIX = re.compile(r"\s+and is all-in")
