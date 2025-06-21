"""Objects used in data"""

import math
from dataclasses import dataclass
from enum import Enum
from functools import total_ordering
from typing import Any, Callable, Optional


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

    def __init__(self, code: str, name_en: str, name_cs: str, parent: Optional[str]):
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

    original_participant_code: Optional[str]
    superevent_rank: int | float  # starting from 1
    superevent_points: int = 0
    four_year_rank: int | float = math.inf
    four_year_points: int = 0

    @property
    def get_four_year_rank_key(self):
        """Get key for a ranking of the current superevent"""
        return -self.four_year_points, -self.superevent_points


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
    order_in_year = 0

    def __repr__(self):
        return f"{self.__class__.__name__}(year={self.year})"

    def whole_years_behind(self, other: Any) -> int:
        """Count whole years which a superevent is behind another superevent"""
        if not isinstance(other, SuperEvent):
            raise ValueError(f"cannot compute distance to {type(other)}")
        years = other.year - self.year
        if self.order_in_year > other.order_in_year:
            years -= 1
        return years


class OlympicGames(SuperEvent):
    event_types = (
        EventType.WINTER_OLYMPIC_GAMES,
        EventType.SUMMER_OLYMPIC_GAMES,
        EventType.THAYER_TRUTT_TROPHY,
    )
    order_in_year = 0

    def __init__(self, year):
        super().__init__(year, self.event_types)


class Championship(SuperEvent):
    event_types = (
        EventType.WORLD_CHAMPIONSHIP,
        EventType.EUROPEAN_CHAMPIONSHIP,
        EventType.DEVELOPMENT_CUP,
    )
    order_in_year = 1

    def __init__(self, year):
        super().__init__(year, self.event_types)


def process_placement_dicts(placement_dicts: list[dict[Participant, Placement]]) -> dict[Participant, Placement]:
    """Join placement sets into a single set, assign points to placements based on their rank"""
    total_participants = 0
    final_placements = {}
    for placement_dict in placement_dicts:
        for participant, placement in placement_dict.items():
            final_placements[participant] = placement
        total_participants += len(placement_dict)

    formula = get_formula(total_participants)
    for placement in final_placements.values():
        if not placement.superevent_points:
            placement.superevent_points = formula(placement.superevent_rank)
    return final_placements


def get_formula(max_rank: int) -> Callable[[int], int]:
    """Create a formula translating rank into points"""
    if max_rank <= 0:
        raise ValueError("max_rank must be positive")
    
    point_breaks = [1, 2, 4, 8]
    points_list = []

    points = 20 * max_rank + sum(max_rank >= pb + 1 for pb in point_breaks) * 20
    for i in range(max_rank):
        points_list.append(points)
        points -= 20
        if i + 1 in point_breaks:
            points -= 20

    def _rank_to_points(rank: int) -> int:
        if rank < 1 or rank > max_rank:
            raise ValueError(f"rank {rank} is out of range [1, {max_rank}]")
        
        return points_list[rank - 1]

    return _rank_to_points
