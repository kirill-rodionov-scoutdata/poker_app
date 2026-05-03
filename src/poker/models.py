from dataclasses import dataclass
from enum import StrEnum


class Source(StrEnum):
    GTO = "gto"
    POPULATION = "population"


class Spot(StrEnum):
    SRP = "SRP"
    THREE_BET_POT = "3BP"


class Formation(StrEnum):
    BB_SB = "BB_SB"
    BB_BTN = "BB_BTN"


class PostflopPosition(StrEnum):
    OOP = "OOP"
    IP = "IP"


class HeroRole(StrEnum):
    PFR = "PFR"
    PFC = "PFC"


class Street(StrEnum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class PlayerPosition(StrEnum):
    SB = "SB"
    BB = "BB"
    BTN = "BTN"
    CO = "CO"
    HJ = "HJ"
    UTG = "UTG"


class ActionType(StrEnum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"


@dataclass
class Action:
    street: Street
    player: str
    action: ActionType
    amount: float | None


@dataclass
class Player:
    name: str
    seat: int
    position: PlayerPosition | None
    stack: float


@dataclass
class ParsedHand:
    hand_id: str
    source: Source
    button_seat: int
    players: list[Player]
    actions: list[Action]
    board: list[str]


@dataclass
class NormalizedHand:
    hand_id: str
    source: Source
    spot: Spot
    formation: Formation | None
    hero_position: PostflopPosition
    hero_role: HeroRole
    street: Street
    line: str
    can_act: bool
    action: ActionType | None
    facing_action: ActionType | None
    first_action: ActionType | None
    action_index: int | None
    action_count: int
    facing_depth: int


class StatStatus(StrEnum):
    OK = "OK"
    NO_DATA = "NO_DATA"
    LOW_SAMPLE = "LOW_SAMPLE"


@dataclass
class SourceResult:
    value: float | None
    sample: int
    status: StatStatus

    def to_dict(self) -> dict:
        return {"value": self.value, "sample": self.sample, "status": str(self.status)}


@dataclass
class StatResult:
    stat_id: str
    label: str
    population: SourceResult
    gto: SourceResult
    delta: float | None

    def to_dict(self) -> dict:
        return {
            "stat_id": self.stat_id,
            "label": self.label,
            "population": self.population.to_dict(),
            "gto": self.gto.to_dict(),
            "delta": self.delta,
        }
