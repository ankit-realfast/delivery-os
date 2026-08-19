from datetime import date

from delivery_os.card import Card
from delivery_os.meters import compute_scoreboard

TODAY = date(2026, 10, 1)


def t2(**kw) -> Card:
    base = dict(id="C-0001", title="t", tier="T2", state="observe", parent=None,
                decider="Priya", eval="evals/x_test.py::test_x",
                value_line="tickets: 40/mo -> 5/mo", kill_criterion="k",
                observation_date=date(2026, 9, 30))
    base.update(kw)
    return Card(intent="x", **base)


def test_card_before_its_observation_date_is_not_due():
    sb = compute_scoreboard([t2(observation_date=date(2026, 12, 1))], today=TODAY)
    assert sb["due"] == []
    assert sb["headline"] is None


def test_due_card_without_a_recorded_outcome_is_chased_not_scored():
    sb = compute_scoreboard([t2(value_moved=None)], today=TODAY)
    assert sb["unrecorded"] == ["C-0001"]
    assert sb["headline"] is None


def test_headline_is_share_of_recorded_cards_whose_value_line_moved():
    cards = [
        t2(id="C-0001", value_moved=True),
        t2(id="C-0002", value_moved=True),
        t2(id="C-0003", value_moved=False),
    ]
    sb = compute_scoreboard(cards, today=TODAY)
    assert sb["headline"] == 0.67
    assert sb["moved"] == ["C-0001", "C-0002"]
    assert sb["not_moved"] == ["C-0003"]


def test_t1_cards_never_enter_the_scoreboard():
    inherited = Card(id="C-0009", title="t", tier="T1", state="observe",
                     parent="C-0001", eval="evals/x_test.py::test_x",
                     observation_date=date(2026, 9, 1), value_moved=True, intent="x")
    assert compute_scoreboard([inherited], today=TODAY)["due"] == []
