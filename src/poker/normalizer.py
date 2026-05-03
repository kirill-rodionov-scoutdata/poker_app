from __future__ import annotations

from poker.models import (
    Action,
    ActionType,
    Formation,
    HeroRole,
    NormalizedHand,
    ParsedHand,
    PlayerPosition,
    PostflopPosition,
    Spot,
    Street,
)

_ACTION_TO_LINE_CODE: dict[ActionType, str] = {
    ActionType.BET: "B",
    ActionType.CHECK: "X",
    ActionType.CALL: "C",
    ActionType.FOLD: "F",
    ActionType.RAISE: "R",
}


class HandNormalizer:

    def normalize(self, parsed_hand: ParsedHand) -> list[NormalizedHand]:
        big_blind_name = self._find_big_blind_name(parsed_hand)
        if big_blind_name is None:
            return []

        preflop_actions = [a for a in parsed_hand.actions if a.street == Street.PREFLOP]
        flop_actions = [a for a in parsed_hand.actions if a.street == Street.FLOP]

        if not flop_actions:
            return []

        spot = self._detect_spot(preflop_actions)
        if spot is None:
            return []

        active_players = self._active_players_at_flop(parsed_hand, preflop_actions)
        if len(active_players) != 2 or big_blind_name not in active_players:
            return []

        opponent_name = next(n for n in active_players if n != big_blind_name)
        formation = self._detect_formation(parsed_hand, opponent_name)
        if formation is None:
            return []

        hero_role = self._detect_hero_role(preflop_actions, big_blind_name)

        big_blind_flop_actions = [a for a in flop_actions if a.player == big_blind_name]
        hero_indices = [i for i, a in enumerate(flop_actions) if a.player == big_blind_name]
        can_act = len(hero_indices) > 0 or any(a.player != big_blind_name for a in flop_actions)

        first_action = big_blind_flop_actions[0].action if big_blind_flop_actions else None
        hero_action = big_blind_flop_actions[-1].action if big_blind_flop_actions else None
        action_count = len(big_blind_flop_actions)

        action_index = None
        for i, a in enumerate(flop_actions):
            if a.player == big_blind_name:
                action_index = i
                break

        # BB_BTN: BB acts first postflop → BB is OOP, BTN is IP
        # BB_SB:  SB acts first postflop → BB is IP,  SB is OOP
        bb_position = (
            PostflopPosition.OOP if formation == Formation.BB_BTN else PostflopPosition.IP
        )
        opponent_position = (
            PostflopPosition.IP if formation == Formation.BB_BTN else PostflopPosition.OOP
        )

        opponent_flop_actions = [a for a in flop_actions if a.player == opponent_name]
        opponent_indices = [i for i, a in enumerate(flop_actions) if a.player == opponent_name]
        opponent_can_act = len(opponent_indices) > 0 or any(a.player != opponent_name for a in flop_actions)

        opponent_first_action = opponent_flop_actions[0].action if opponent_flop_actions else None
        opponent_action = opponent_flop_actions[-1].action if opponent_flop_actions else None
        opponent_action_count = len(opponent_flop_actions)

        opponent_action_index = None
        for i, a in enumerate(flop_actions):
            if a.player == opponent_name:
                opponent_action_index = i
                break
        opponent_role = self._detect_hero_role(preflop_actions, opponent_name)

        bb_facing_action, bb_depth = self._get_facing_action(big_blind_name, opponent_name, flop_actions)
        opponent_facing_action, opponent_depth = self._get_facing_action(opponent_name, big_blind_name, flop_actions)

        if can_act and action_index is None:
            # inconsistent: игрок должен был действовать, но не найдено действие
            return []

        if opponent_can_act and opponent_action_index is None:
            # inconsistent: игрок должен был действовать, но не найдено действие
            return []

        return [
            NormalizedHand(
                hand_id=parsed_hand.hand_id,
                source=parsed_hand.source,
                spot=spot,
                formation=formation,
                hero_position=bb_position,
                hero_role=hero_role,
                street=Street.FLOP,
                line=self._encode_line(big_blind_flop_actions),
                can_act=can_act,
                action=hero_action,
                facing_action=bb_facing_action,
                first_action=first_action,
                action_index=action_index,
                action_count=action_count,
                facing_depth=bb_depth,
            ),
            NormalizedHand(
                hand_id=parsed_hand.hand_id,
                source=parsed_hand.source,
                spot=spot,
                formation=formation,
                hero_position=opponent_position,
                hero_role=opponent_role,
                street=Street.FLOP,
                line=self._encode_line(opponent_flop_actions),
                can_act=opponent_can_act,
                action=opponent_action,
                facing_action=opponent_facing_action,
                first_action=opponent_first_action,
                action_index=opponent_action_index,
                action_count=opponent_action_count,
                facing_depth=opponent_depth,
            ),
        ]

    def _find_big_blind_name(self, parsed_hand: ParsedHand) -> str | None:
        return next(
            (p.name for p in parsed_hand.players if p.position == PlayerPosition.BB),
            None,
        )

    def _detect_spot(self, preflop_actions: list[Action]) -> Spot | None:
        raise_count = sum(1 for a in preflop_actions if a.action == ActionType.RAISE)
        if raise_count == 1:
            return Spot.SRP
        if raise_count == 2:
            return Spot.THREE_BET_POT
        return None

    def _active_players_at_flop(
        self, parsed_hand: ParsedHand, preflop_actions: list[Action]
    ) -> set[str]:
        active = {p.name for p in parsed_hand.players}

        for action in preflop_actions:
            if action.action == ActionType.FOLD:
                active.discard(action.player)

        return active

    def _detect_formation(
        self, parsed_hand: ParsedHand, opponent_name: str
    ) -> Formation | None:
        opponent_position = next(
            (p.position for p in parsed_hand.players if p.name == opponent_name),
            None,
        )
        if opponent_position == PlayerPosition.SB:
            return Formation.BB_SB
        if opponent_position == PlayerPosition.BTN:
            return Formation.BB_BTN
        return None

    def _detect_hero_role(
        self, preflop_actions: list[Action], big_blind_name: str
    ) -> HeroRole:
        preflop_raises = [a for a in preflop_actions if a.action == ActionType.RAISE]
        if preflop_raises and preflop_raises[-1].player == big_blind_name:
            return HeroRole.PFR
        return HeroRole.PFC

    def _get_facing_action(
        self,
        hero_name: str,
        opponent_name: str,
        flop_actions: list[Action],
    ) -> tuple[ActionType | None, int]:
        hero_first_index = None

        for i, action in enumerate(flop_actions):
            if action.player == hero_name:
                hero_first_index = i
                break

        if hero_first_index is None:
            return None, 0

        depth = 0
        for action in flop_actions[:hero_first_index]:
            if action.player == opponent_name:
                depth += 1
                return action.action, depth

        return None, depth

    def _encode_line(self, actions: list[Action]) -> str:
        return "".join(
            _ACTION_TO_LINE_CODE[a.action]
            for a in actions
            if a.action in _ACTION_TO_LINE_CODE
        )
