"""Objects used in data"""

from dataclasses import dataclass
from enum import Enum
from functools import total_ordering
from typing import Callable, Optional


class EventType(Enum):
    """Type of event"""

    WINTER_OLYMPIC_GAMES = 1
    SUMMER_OLYMPIC_GAMES = 2
    WORLD_CHAMPIONSHIP = 3
    EUROPEAN_CHAMPIONSHIP = 4
    THAYER_TRUTT_TROPHY = 5
    DEVELOPMENT_CUP = 6


@total_ordering
class Participant:
    """Participant of a (super)event, usually a country"""

    all_participants = {}

    def __init__(self, code: str, name_en: str, name_cs: str, parent: str):
        self._code = code
        self._name_en = name_en
        self._name_cs = name_cs
        self._parent = parent
        Participant.all_participants[self._code] = self

    def __lt__(self, other):
        return self.code < other.code

    def __eq__(self, other):
        return self.code == other.code

    def __hash__(self):
        return self._code.__hash__()

    def __repr__(self):
        return f"Participant(code={self.code})"

    @property
    def code(self):
        return self._code

    @property
    def name_en(self):
        return self._name_en

    @property
    def name_cs(self):
        return self._name_cs

    @property
    def parent(self):
        return self._parent

    @classmethod
    def get_participant(cls, code: str) -> Optional["Participant"]:
        return cls.all_participants.get(code)


@dataclass
class Placement:
    """Placement of a participant within a (super)event"""

    rank: int  # starting from 1
    points: Optional[int] = None


@dataclass(frozen=True)
class Event:
    """Held ice hockey tournament"""

    year: int
    type_: EventType


@dataclass(frozen=True)
class SuperEvent:
    """Group of events with a strict ordering"""

    year: int
    event_types: list[EventType]

    def __repr__(self):
        return f"{self.__class__.__name__}(year={self.year})"


class OlympicGames(SuperEvent):
    event_types = (
        EventType.WINTER_OLYMPIC_GAMES,
        EventType.SUMMER_OLYMPIC_GAMES,
        EventType.THAYER_TRUTT_TROPHY,
    )

    def __init__(self, year):
        super().__init__(year, self.event_types)


class Championship(SuperEvent):
    event_types = (
        EventType.WORLD_CHAMPIONSHIP,
        EventType.EUROPEAN_CHAMPIONSHIP,
        EventType.DEVELOPMENT_CUP,
    )

    def __init__(self, year):
        super().__init__(year, self.event_types)


def process_placement_dicts(placement_dicts: list[dict[Participant, Placement]]) -> dict[Participant, Placement]:
    """Join placement sets into a single set, assign points to placements based on their rank"""
    previous_max_rank = 0
    final_placements = {}
    for placement_dict in placement_dicts:
        # get last participant's rank in case ranks could not be shared
        # count of participants cannot be used due to non-systematic ranks
        # of suspended Russia and Belarus
        ranks = [placement.rank for placement in placement_dict.values()]
        max_rank = max(ranks)
        max_rank_cardinality = ranks.count(max_rank)
        max_rank += max_rank_cardinality

        for participant, placement in placement_dict.items():
            placement.rank += previous_max_rank
            final_placements[participant] = placement

        previous_max_rank += max_rank

    formula = get_formula(previous_max_rank)
    for placement in final_placements.values():
        placement.points = formula(placement.rank)
    return final_placements


def get_formula(max_rank: int) -> Callable[[int], int]:
    """Create a formula translating rank into points"""
    point_breaks = [1, 2, 8]
    points_list = []

    points = 20 * max_rank + sum(max_rank >= pb + 1 for pb in point_breaks) * 20
    for i in range(max_rank):
        points_list.append(points)
        points -= 20
        if i + 1 in point_breaks:
            points -= 20

    def _rank_to_points(rank):
        return points_list[rank - 1]

    return _rank_to_points
