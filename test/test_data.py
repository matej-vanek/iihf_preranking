import pandas as pd

from iihf.data import process_events
from iihf.objects import Championship, Event, EventType, OlympicGames, Participant, Placement


def test_process_events():
    events = {
        Event(1111, EventType.DEVELOPMENT_CUP): {Participant("AAA", "aaa", "aaa", None): Placement(1, 20)},
        Event(1111, EventType.WORLD_CHAMPIONSHIP): {Participant("BBB", "bbb", "bbb", None): Placement(1, 20)},
        Event(1111, EventType.WINTER_OLYMPIC_GAMES): {Participant("CCC", "ccc", "ccc", None): Placement(1, 20)},
        Event(1112, EventType.DEVELOPMENT_CUP): {Participant("DDD", "ddd", "ddd", None): Placement(1, 20)},
    }
    result = pd.DataFrame(
        {
            OlympicGames(1111): {Participant("CCC", "ccc", "ccc", None): Placement(1, 20)},
            Championship(1111): {
                Participant("BBB", "bbb", "bbb", None): Placement(1, 60),
                Participant("AAA", "aaa", "aaa", None): Placement(2, 20),
            },
            Championship(1112): {Participant("DDD", "ddd", "ddd", None): Placement(1, 20)},
        }
    )
    assert process_events(events).sort_index(inplace=True) == result.sort_index(inplace=True)
