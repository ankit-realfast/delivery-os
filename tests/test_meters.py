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
    # C-0002 has an eval but has never been run, so it is presumed broken
    # (spec 5) and does not count toward fallibility.
    assert m2["headline"] == 0.0


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
    proven = card(id="C-0002", state="commit", history=[
        {"state": "verify", "at": "2026-08-01T09:00:00+00:00", "by": "ci", "verify": "fail"},
    ])
    m2 = compute_m2([card(id="C-0001", state="commit", eval=None), proven])
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


def test_m1_ignores_verify_entries_that_share_a_state_name():
    c = card(state="commit", decider="Priya", history=[
        {"state": "contest", "at": "2026-08-01T09:00:00+00:00", "by": "x"},
        {"state": "commit", "at": "2026-08-02T09:00:00+00:00", "by": "x"},
        {"state": "commit", "at": "2026-08-03T09:00:00+00:00", "by": "ci", "verify": "pass"},
    ])
    assert compute_m1([c], now=NOW)["median_hours"] == 24.0


def test_m2_flags_a_never_run_eval_as_presumed_broken():
    # DELIBERATE REVERSAL of the previous
    # test_m2_does_not_flag_a_card_with_no_verify_history. Spec 5 says an
    # eval that has never been red is presumed broken until it goes red
    # once; an eval that has never *run* has certainly never been red, so
    # exempting it was the plan disagreeing with the spec. The spec wins.
    c = card(id="C-0001", state="commit")   # has an eval, empty history
    m2 = compute_m2([c])
    assert m2["never_run"] == ["C-0001"]
    assert m2["never_red"] == []            # it has not run, so it has not "gone green"
    assert m2["presumed_broken"] == ["C-0001"]
    assert m2["headline"] == 0.0


def test_m2_headline_is_fallibility_not_presence():
    # THE C2 DEFECT, stated as a test: a corpus where nothing has ever been
    # verified must not report full eval coverage. contract/reciprocal-sla.md
    # obliges sharing this number with the client.
    corpus = [card(id="C-0001", state="commit"), card(id="C-0002", state="verify")]
    m2 = compute_m2(corpus)
    assert m2["with_eval"] == 2          # both have an eval string
    assert m2["headline"] == 0.0         # neither has been proven able to fail
    assert m2["presumed_broken"] == ["C-0001", "C-0002"]


def test_m2_counts_a_card_that_has_gone_red_once_and_then_green():
    c = card(id="C-0001", state="verify", history=[
        {"state": "verify", "at": "2026-08-01T09:00:00+00:00", "by": "ci", "verify": "fail"},
        {"state": "verify", "at": "2026-08-01T10:00:00+00:00", "by": "ci", "verify": "pass"},
    ])
    m2 = compute_m2([c])
    assert m2["headline"] == 1.0
    assert m2["presumed_broken"] == []


def test_m2_separates_never_run_from_never_red():
    never_run = card(id="C-0001", state="commit")
    never_red = card(id="C-0002", state="verify", history=[
        {"state": "verify", "at": "2026-08-01T09:00:00+00:00", "by": "ci", "verify": "pass"},
    ])
    m2 = compute_m2([never_run, never_red])
    assert m2["never_run"] == ["C-0001"]
    assert m2["never_red"] == ["C-0002"]


def test_m2_survives_an_unrecognised_state():
    # state_at_least fails closed: a typo must not silently drop a card out
    # of the client-facing meter.
    assert compute_m2([card(id="C-0001", state="Commit")])["in_scope"] == 1
