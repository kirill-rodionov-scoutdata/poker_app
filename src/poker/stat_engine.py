from poker.models import (
    ActionType,
    Formation,
    HeroRole,
    NormalizedHand,
    PostflopPosition,
    Spot,
    Street,
)

_STATE_SKIP = {"NO_STAT", "INVALID_CONTEXT"}

_SPOT_MAP: dict[str, Spot] = {
    "SRP": Spot.SRP,
    "3BP": Spot.THREE_BET_POT,
}

_FORMATION_MAP: dict[str, Formation] = {
    "BB_SB": Formation.BB_SB,
    "BB_BTN": Formation.BB_BTN,
}

_POSITION_MAP: dict[str, PostflopPosition] = {
    "OOP": PostflopPosition.OOP,
    "IP": PostflopPosition.IP,
}

_ROLE_MAP: dict[str, HeroRole] = {
    "PFR": HeroRole.PFR,
    "PFC": HeroRole.PFC,
}

_STREET_MAP: dict[str, Street] = {
    "preflop": Street.PREFLOP,
    "flop": Street.FLOP,
    "turn": Street.TURN,
    "river": Street.RIVER,
}

_ACTION_MAP: dict[str, ActionType] = {
    "bet": ActionType.BET,
    "check": ActionType.CHECK,
    "call": ActionType.CALL,
    "fold": ActionType.FOLD,
    "raise": ActionType.RAISE,
}


class StatComputer:
    """Computes numerator and denominator for a single stat definition."""

    def compute(
        self,
        stat: dict,
        hands: list[NormalizedHand],
    ) -> tuple[int, int]:
        if stat.get("state") in _STATE_SKIP:
            return 0, 0

        if stat.get("bindingMode") != "DIRECT_EXACT":
            return 0, 0

        context_filters = stat.get("contextFilters", {})
        ok, spot_filter = _map_or_none(context_filters.get("spot"), _SPOT_MAP)
        if not ok:
            return 0, 0
        ok, formation_filter = _map_or_none(
            context_filters.get("formation"), _FORMATION_MAP
        )
        if not ok:
            return 0, 0
        ok, position_filter = _map_or_none(
            context_filters.get("position"), _POSITION_MAP
        )
        if not ok:
            return 0, 0
        ok, role_filter = _map_or_none(context_filters.get("role"), _ROLE_MAP)
        if not ok:
            return 0, 0
        ok, street_filter = _map_or_none(context_filters.get("street"), _STREET_MAP)
        if not ok:
            return 0, 0

        opportunity = stat.get("opportunity", {})
        ok, opportunity_street = _map_or_none(opportunity.get("street"), _STREET_MAP)
        if not ok:
            return 0, 0
        opportunity_can_act = opportunity.get("canAct")

        ok, facing_action_filter = _map_or_none(
            opportunity.get("facingAction"), _ACTION_MAP
        )
        if not ok:
            return 0, 0
        use_facing = (
            "facingAction" in opportunity
            and opportunity.get("facingAction") is not None
        )

        success = stat.get("success", {})
        ok, success_street = _map_or_none(success.get("street"), _STREET_MAP)
        if not ok:
            return 0, 0
        ok, success_action = _map_or_none(success.get("action"), _ACTION_MAP)
        if not ok:
            return 0, 0

        if opportunity_street is not None and opportunity_street != Street.FLOP:
            return 0, 0

        if success_street is not None and success_street != Street.FLOP:
            return 0, 0

        numerator = 0
        denominator = 0

        for hand in hands:
            if hand.can_act and hand.action is None and hand.first_action is None:
                continue

            if spot_filter is not None and hand.spot != spot_filter:
                continue
            if formation_filter is not None and hand.formation != formation_filter:
                continue
            if position_filter is not None and hand.hero_position != position_filter:
                continue
            if role_filter is not None and hand.hero_role != role_filter:
                continue
            if street_filter is not None and hand.street != street_filter:
                continue

            if use_facing:
                if hand.facing_action != facing_action_filter:
                    continue

                # depth-aware фильтр (если есть)
                if "maxFacingDepth" in opportunity:
                    if hand.action_count > opportunity["maxFacingDepth"]:
                        continue
            else:
                if opportunity_can_act is not None:
                    if hand.can_act != opportunity_can_act:
                        continue

            if "maxActionIndex" in opportunity:
                if (
                    hand.action_index is not None
                    and hand.action_index > opportunity["maxActionIndex"]
                ):
                    continue

            denominator += 1

            if success_action is not None:
                if "useFirstAction" in success and success.get("useFirstAction"):
                    if hand.first_action != success_action:
                        continue
                elif "useFirstAction" not in success and hand.action_count > 1:
                    # если много действий, используем first_action по умолчанию
                    if hand.first_action != success_action:
                        continue
                else:
                    if hand.action != success_action:
                        continue

            numerator += 1

        return numerator, denominator


def compute_stat(
    stat: dict,
    hands: list[NormalizedHand],
) -> tuple[int, int]:
    """Backward-compatible function wrapper around StatComputer.compute()."""
    return StatComputer().compute(stat, hands)


def _map_or_none(
    value: str | None, mapping: dict[str, object]
) -> tuple[bool, object | None]:
    if value is None:
        return True, None
    mapped = mapping.get(value)
    if mapped is None:
        return False, None
    return True, mapped
