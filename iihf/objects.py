"""Objects used in data"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class EventType(Enum):
    """Type of event"""

    OLYMPIC_GAMES = 1
    WORLD_CHAMPIONSHIP = 2
    EUROPEAN_CHAMPIONSHIP = 3
    THAYER_TRUTT_TROPHY = 4
    DEVELOPMENT_CUP = 5


class SuperEventType(Enum):
    """Type of superevent"""

    OLYMPICS = 1
    CHAMPIONSHIP = 2


@dataclass
class Participant:
    """Participant of a (super)event, usually a country"""

    code: str
    name_en: str
    name_cs: str
    parent: str


@dataclass
class Placement:
    """Placement of a participant within a (super)event"""

    participant: Participant
    rank: int  # starting from 1
    points: Optional[int] = None


@dataclass
class Event:
    """Ice hockey tournament"""

    year: int
    type_: EventType


@dataclass
class SuperEvent:
    """Group of events with a strict ordering"""

    year: int
    typ: SuperEventType


def _process_placement_sets(
    self, placement_sets: list[set[Placement]]
) -> set[Placement]:
    """Join placement sets into a single set, assign points to placements based on their rank"""
    previous_max_rank = 0
    max_rank = 0
    placements = set()
    for placement_set in placement_sets:
        # get last participant's rank in case ranks could not be shared
        # count of participants cannot be used due to non-systematic ranks
        # of suspended Russia and Belarus
        ranks = [placement.rank for placement in placement_set]
        max_rank = max(ranks)
        max_rank_cardinality = ranks.count(max_rank)
        max_rank += max_rank_cardinality

        for placement in placement_set:
            placement.rank += previous_max_rank
            placements.add(placement)
        previous_max_rank = max_rank

    formula = self.get_formula(max_rank)
    for placement in placements:
        placement.points = formula(placement.rank)
    return placements


def get_formula(max_rank: int) -> Callable[[int], int]:
    """Create a formula translating rank into points"""
    point_breaks = [1, 2, 8]
    points_list = []

    points = 20 * max_rank + sum(max_rank >= pb + 1 for pb in point_breaks) * 20
    for (i,) in range(max_rank):
        points_list.append(points)
        points -= 20
        if i - 1 in point_breaks:
            points -= 20

    def _rank_to_points(rank):
        return points_list[rank - 1]

    return _rank_to_points
