import pytest

from iihf.objects import Participant, Placement, get_formula, process_placement_dicts


def test_process_placement_dicts():
    placement_dicts = [
        {
            Participant("AAA", "aaa", "aaa", None): Placement("AAA", 1, 100),
            Participant("BBB", "bbb", "bbb", None): Placement("BBB", 2, 40),
            Participant("CCC", "ccc", "ccc", None): Placement("CCC", 2, 40),
        },
        {Participant("DDD", "ddd", "ddd", None): Placement("DDD", 1, 20)},
    ]
    result = {
        Participant("AAA", "aaa", "aaa", None): Placement("AAA", 1, 120),
        Participant("BBB", "bbb", "bbb", None): Placement("BBB", 2, 80),
        Participant("CCC", "ccc", "ccc", None): Placement("CCC", 2, 80),
        Participant("DDD", "ddd", "ddd", None): Placement("DDD", 4, 20),
    }
    assert process_placement_dicts(placement_dicts) == result


@pytest.mark.parametrize(
    ("max_rank", "result"),
    [
        (1, {1: 20}),
        (3, {1: 100, 2: 60, 3: 20}),
        (10, {1: 260, 2: 220, 3: 180, 4: 160, 5: 140, 6: 120, 7: 100, 8: 80, 9: 40, 10: 20}),
    ],
)
def test_get_formula(max_rank, result):
    formula = get_formula(max_rank)
    for rank, value in result.items():
        assert value == formula(rank)
