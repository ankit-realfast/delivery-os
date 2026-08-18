from datetime import datetime, timezone

from delivery_os.card import Card
from delivery_os.meters import compute_m1, compute_m2, compute_m3

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def card(**kw) -> Card:
    base = dict(id="C-0001", title="t", tier="T1", state="draft", parent="C-0000",
                eval="evals/x_test.py::test_x")
    base.update(kw)
    return Card(intent="x", **base)


def hist(*pairs):
    return [{"state": s, "at": at, "by": "x"} for s, at in pairs]


def test_m1_measures_contest_to_commit_in_hours():
    c = card(state="commit", decider="Priya", history=hist(
        ("contest", "2026-08-01T09:00:00+00:00"),
        ("commit", "2026-08-02T09:00:00+00:00"),
    ))
    m1 = compute_m1([c], now=NOW)
    assert m1["median_hours"] == 24.0
    assert m1["by_decider"]["Priya"] == 24.0


def test_m1_reports_open_cards_aging_in_contest():
    c = card(state="contest", decider="Priya", history=hist(
        ("contest", "2026-08-18T12:00:00+00:00"),
    ))
    m1 = compute_m1([c], now=NOW)
    assert m1["open"] == [{"id": "C-0001", "decider": "Priya", "hours": 24.0}]
    assert m1["median_hours"] is None


def test_m1_uses_the_last_contest_entry_when_a_card_bounced():
    c = card(state="commit", decider="Priya", history=hist(
        ("contest", "2026-08-01T09:00:00+00:00"),
        ("draft", "2026-08-01T10:00:00+00:00"),
        ("contest", "2026-08-02T09:00:00+00:00"),
        ("commit", "2026-08-02T15:00:00+00:00"),
    ))
    assert compute_m1([c], now=NOW)["median_hours"] == 6.0


def test_m2_counts_only_cards_at_commit_or_later():
    drafted = card(id="C-0001", state="draft", eval=None)
    committed = card(id="C-0002", state="commit")
    m2 = compute_m2([drafted, committed])
    assert m2["in_scope"] == 1
    assert m2["with_eval"] == 1
    assert m2["headline"] == 1.0


def test_m2_flags_evals_that_have_never_been_red():
    never_red = card(id="C-0001", state="verify", history=[
        {"state": "verify", "at": "2026-08-01T09:00:00+00:00", "by": "ci", "verify": "pass"},
    ])
    been_red = card(id="C-0002", state="verify", history=[
        {"state": "verify", "at": "2026-08-01T09:00:00+00:00", "by": "ci", "verify": "fail"},
        {"state": "verify", "at": "2026-08-01T10:00:00+00:00", "by": "ci", "verify": "pass"},
    ])
    assert compute_m2([never_red, been_red])["never_red"] == ["C-0001"]


def test_m2_missing_eval_lowers_the_headline():
    m2 = compute_m2([card(id="C-0001", state="commit", eval=None),
                     card(id="C-0002", state="commit")])
    assert m2["headline"] == 0.5
    assert m2["without_eval"] == ["C-0001"]


def test_m3_counts_live_nonzero_deltas_and_names_the_unowned():
    owned = card(id="C-0001", state="build", tier="T2",
                 behaviour_delta="ops stops using the sheet", delta_owner="Sam")
    unowned = card(id="C-0002", state="build", tier="T2",
                   behaviour_delta="finance re-codes invoices")
    closed = card(id="C-0003", state="closed", tier="T2",
                  behaviour_delta="already absorbed", delta_owner="Sam")
    m3 = compute_m3([owned, unowned, closed])
    assert m3["live_deltas"] == 2
    assert m3["unowned"] == ["C-0002"]


def test_m3_is_zero_when_every_card_absorbed_the_process():
    assert compute_m3([card(state="build")])["live_deltas"] == 0
