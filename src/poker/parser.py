import re
from pathlib import Path

import poker.patterns as P
from poker.models import (
    Action,
    ActionType,
    ParsedHand,
    Player,
    PlayerPosition,
    Source,
    Street,
)

_VERB_TO_ACTION: dict[str, ActionType] = {
    "folds": ActionType.FOLD,
    "checks": ActionType.CHECK,
    "calls": ActionType.CALL,
    "bets": ActionType.BET,
    "raises": ActionType.RAISE,
}

_GTO_NAME_TO_POSITION: dict[str, PlayerPosition] = {
    "UTG": PlayerPosition.UTG,
    "HJ": PlayerPosition.HJ,
    "CO": PlayerPosition.CO,
    "BU": PlayerPosition.BTN,
    "SB": PlayerPosition.SB,
    "BB": PlayerPosition.BB,
}

_SEAT_OFFSET_TO_POSITION: dict[int, PlayerPosition] = {
    0: PlayerPosition.BTN,
    1: PlayerPosition.CO,
    2: PlayerPosition.HJ,
    3: PlayerPosition.UTG,
    4: PlayerPosition.SB,
    5: PlayerPosition.BB,
}

_SUMMARY_LABEL_TO_POSITION: dict[str, PlayerPosition] = {
    "small blind": PlayerPosition.SB,
    "big blind": PlayerPosition.BB,
    "button": PlayerPosition.BTN,
}


class HandParser:
    def parse_file(self, path: Path, source: Source) -> list[ParsedHand]:
        text = path.read_text(encoding="utf-8", errors="replace")
        results: list[ParsedHand] = []
        for block in self._split_blocks(text):
            hand = self._parse_block(block, source)
            if hand is not None:
                results.append(hand)
        return results

    def _split_blocks(self, text: str) -> list[str]:
        positions = [m.start() for m in P.HAND_HEADER.finditer(text)]
        if not positions:
            return []
        blocks: list[str] = []
        for index, start in enumerate(positions):
            end = positions[index + 1] if index + 1 < len(positions) else len(text)
            block = text[start:end].strip()
            if block:
                blocks.append(block)
        return blocks

    def _parse_block(self, block: str, source: Source) -> ParsedHand | None:
        lines = block.splitlines()
        if not lines:
            return None
        fmt = self._detect_format(lines[0])
        if fmt is None:
            return None
        if fmt in ("gto", "wpn_ps"):
            return self._parse_colon_format(lines, source, fmt)
        return self._parse_nocolon_format(lines, source)

    def _detect_format(self, first_line: str) -> str | None:
        if P.GTO_HEADER.match(first_line):
            return "gto"
        if P.WPN_PS_HEADER.match(first_line):
            return "wpn_ps"
        if P.WPN_HIS_HEADER.match(first_line):
            return "wpn_his"
        return None

    def _parse_colon_format(
        self, lines: list[str], source: Source, fmt: str
    ) -> ParsedHand | None:
        hand_id = self._extract_hand_id(lines[0], fmt)
        if hand_id is None:
            return None
        button_seat, seat_to_player, seat_to_stack = self._extract_seats(lines)
        if button_seat is None:
            return None
        actions, board = self._collect_actions_and_board(lines, P.ACTION_COLON)
        players = self._build_players(
            seat_to_player,
            seat_to_stack,
            button_seat,
            self._extract_summary_positions(lines),
            fmt,
        )
        return ParsedHand(
            hand_id=hand_id,
            source=source,
            button_seat=button_seat,
            players=players,
            actions=actions,
            board=board,
        )

    def _parse_nocolon_format(
        self, lines: list[str], source: Source
    ) -> ParsedHand | None:
        hand_id = self._extract_hand_id(lines[0], "wpn_his")
        if hand_id is None:
            return None
        button_seat, seat_to_player, seat_to_stack = self._extract_seats(lines)
        if button_seat is None:
            return None
        known_names = sorted(seat_to_player.values(), key=len, reverse=True)
        escaped = "|".join(re.escape(n) for n in known_names)
        action_pattern = re.compile(
            rf"^({escaped}) (folds|checks|calls|bets|raises)"
            r"(?:\s+\$([0-9.]+))?(?:\s+to\s+\$([0-9.]+))?"
        )
        actions, board = self._collect_actions_and_board(
            lines, action_pattern, strip_all_in=True
        )
        players = self._build_players(
            seat_to_player,
            seat_to_stack,
            button_seat,
            self._extract_summary_positions(lines),
            "wpn_his",
        )
        return ParsedHand(
            hand_id=hand_id,
            source=source,
            button_seat=button_seat,
            players=players,
            actions=actions,
            board=board,
        )

    def _collect_actions_and_board(
        self,
        lines: list[str],
        action_pattern: re.Pattern,
        *,
        strip_all_in: bool = False,
    ) -> tuple[list[Action], list[str]]:
        actions: list[Action] = []
        board: list[str] = []
        current_street = Street.PREFLOP

        for raw in lines:
            line = raw.strip()
            if strip_all_in:
                line = P.ALL_IN_SUFFIX.sub("", line)

            street_match = P.STREET_HEADER.match(line)
            if street_match:
                keyword = street_match.group(1)
                if keyword == "HOLE CARDS":
                    current_street = Street.PREFLOP
                elif keyword == "FLOP":
                    current_street = Street.FLOP
                    flop_match = P.FLOP_CARDS.match(line)
                    if flop_match:
                        board = flop_match.group(1).split()
                elif keyword == "TURN":
                    current_street = Street.TURN
                elif keyword == "RIVER":
                    current_street = Street.RIVER
                elif keyword in ("SHOW DOWN", "SUMMARY"):
                    break
                continue

            if P.SKIP_LINE.match(line):
                continue

            action_match = action_pattern.match(line)
            if action_match:
                verb = action_match.group(2)
                amount_raw = action_match.group(4) or action_match.group(3)
                actions.append(
                    Action(
                        street=current_street,
                        player=action_match.group(1),
                        action=_VERB_TO_ACTION[verb],
                        amount=float(amount_raw) if amount_raw else None,
                    )
                )

        return actions, board

    def _extract_hand_id(self, first_line: str, fmt: str) -> str | None:
        if fmt == "gto":
            match = P.GTO_HEADER.match(first_line)
        elif fmt == "wpn_ps":
            match = P.WPN_PS_HEADER.match(first_line)
        else:
            match = P.WPN_HIS_HEADER.match(first_line)
        return match.group(1) if match else None

    def _extract_seats(
        self, lines: list[str]
    ) -> tuple[int | None, dict[int, str], dict[int, float]]:
        button_seat: int | None = None
        seat_to_player: dict[int, str] = {}
        seat_to_stack: dict[int, float] = {}
        in_summary = False

        for raw in lines:
            line = raw.strip()
            if "*** SUMMARY ***" in line:
                in_summary = True
            if in_summary:
                continue
            button_match = P.BUTTON_SEAT.search(line)
            if button_match:
                button_seat = int(button_match.group(1))
            seat_match = P.SEAT.match(line)
            if seat_match:
                seat_to_player[int(seat_match.group(1))] = seat_match.group(2).strip()
                seat_to_stack[int(seat_match.group(1))] = float(seat_match.group(3))

        return button_seat, seat_to_player, seat_to_stack

    def _extract_summary_positions(self, lines: list[str]) -> dict[str, PlayerPosition]:
        position_map: dict[str, PlayerPosition] = {}
        in_summary = False
        for raw in lines:
            line = raw.strip()
            if "*** SUMMARY ***" in line:
                in_summary = True
                continue
            if not in_summary:
                continue
            match = P.SUMMARY_POSITION.match(line)
            if match:
                position = _SUMMARY_LABEL_TO_POSITION.get(match.group(2))
                if position is not None:
                    position_map[match.group(1)] = position
        return position_map

    def _build_players(
        self,
        seat_to_player: dict[int, str],
        seat_to_stack: dict[int, float],
        button_seat: int,
        summary_positions: dict[str, PlayerPosition],
        fmt: str,
    ) -> list[Player]:
        seat_numbers = sorted(seat_to_player.keys())
        button_index = (
            seat_numbers.index(button_seat) if button_seat in seat_numbers else 0
        )
        total_seats = len(seat_numbers)
        players: list[Player] = []

        for seat_number in seat_numbers:
            name = seat_to_player[seat_number]
            stack = seat_to_stack.get(seat_number, 0.0)
            if fmt == "gto":
                position: PlayerPosition | None = _GTO_NAME_TO_POSITION.get(
                    name.upper()
                )
            elif name in summary_positions:
                position = summary_positions[name]
            else:
                offset = (seat_numbers.index(seat_number) - button_index) % total_seats
                position = _SEAT_OFFSET_TO_POSITION.get(offset)
            players.append(
                Player(name=name, seat=seat_number, position=position, stack=stack)
            )

        return players
