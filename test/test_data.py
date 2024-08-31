import pandas as pd

from iihf.data import process_events, process_four_years
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


def test_process_four_years():
    data = pd.DataFrame(
        {
            Championship(9): Placement("AAA", 1, 900),
            Championship(12): Placement("AAA", 1, 1200),  # empty years
            Championship(13): Placement("AAA", 1, 1300),
            OlympicGames(14): Placement("AAA", 1, 1400),  # only Olympics
            Championship(15): Placement("AAA", 1, 1500),
            OlympicGames(16): Placement("AAA", 1, 1600),  # Olympics + Championship, Olympics after 2 years
            Championship(16): Placement("AAA", 1, 1604),
            Championship(17): Placement("AAA", 1, 1700),
            Championship(18): Placement("AAA", 1, 1800),
            Championship(19): Placement("AAA", 1, 1900),
            OlympicGames(20): Placement("AAA", 1, 2000),  # handle superevent order in year
            Championship(20): Placement("AAA", 1, 2004),
        },
        index=["AAA"],
    )
    data = process_four_years(data)
    assert [p.four_year_points for p in data.iloc[0, :]] == [
        900,
        1425,
        2200,
        3600,
        3500,
        4050,
        4654,
        4853,
        5052,
        4901,
        6501,
        6754,
    ]
