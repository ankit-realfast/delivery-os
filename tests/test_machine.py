from datetime import datetime, timezone

import pytest

from delivery_os.card import Card
from delivery_os.machine import IllegalTransition, move_card, record_verify

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def card(state="draft", **kw) -> Card:
    base = dict(id="C-0002", title="t", tier="T1", state=state, parent="C-0001",
                eval="evals/C-0002_test.py::test_x")
    base.update(kw)
    return Card(intent="x", **base)


def test_move_appends_history_and_sets_state():
    moved = move_card(card(), "contest", by="akp", now=NOW)
    assert moved.state == "contest"
    assert moved.history[-1] == {"state": "contest", "at": "2026-08-19T12:00:00+00:00", "by": "akp"}


def test_move_does_not_mutate_the_original():
    original = card()
    move_card(original, "contest", by="akp", now=NOW)
    assert original.state == "draft"
    assert original.history == []


def test_t1_card_skips_contest_entirely():
    # Spec 4: "T1 - reversible. No contest." A T1 card needs no client decision.
    assert move_card(card("draft", tier="T1"), "commit", by="akp", now=NOW).state == "commit"


def test_t2_card_may_not_skip_contest():
    with pytest.raises(IllegalTransition, match="draft -> commit"):
        move_card(card("draft", tier="T2"), "commit", by="akp", now=NOW)


def test_illegal_transition_is_refused():
    with pytest.raises(IllegalTransition, match="commit -> observe"):
        move_card(card("commit"), "observe", by="akp", now=NOW)


def test_contest_can_return_to_draft():
    assert move_card(card("contest"), "draft", by="akp", now=NOW).state == "draft"


def test_verify_failure_with_wrong_build_goes_back_to_build():
    assert move_card(card("verify"), "build", by="akp", now=NOW).state == "build"


def test_verify_failure_with_right_build_goes_back_to_contest():
    assert move_card(card("verify"), "contest", by="akp", now=NOW).state == "contest"


def test_record_verify_writes_pass_into_history():
    c = record_verify(card("verify"), passed=True, by="ci", now=NOW)
    assert c.history[-1]["verify"] == "pass"
    assert c.state == "verify"


def test_record_verify_writes_fail_into_history():
    c = record_verify(card("verify"), passed=False, by="ci", now=NOW)
    assert c.history[-1]["verify"] == "fail"


def test_record_verify_does_not_mutate_the_original():
    original = card("verify")
    record_verify(original, passed=True, by="ci", now=NOW)
    assert original.state == "verify"
    assert original.history == []


def test_t1_fast_path_does_not_leak_past_draft():
    # The fast path appends "commit" to the legal set. Pick a state where
    # "commit" is not already legal, or a leak is invisible.
    with pytest.raises(IllegalTransition, match="build -> commit"):
        move_card(card("build", tier="T1"), "commit", by="akp", now=NOW)


def test_under_tiered_card_cannot_use_the_t1_fast_path():
    # C4: the card claims T1 but touches auth, so it derives T2 and must
    # pass through contest. Authoring cannot buy the fast lane.
    with pytest.raises(IllegalTransition, match="draft -> commit"):
        move_card(card("draft", tier="T1", touches_auth=True), "commit", by="akp", now=NOW)


def test_orphan_card_claiming_t1_cannot_use_the_fast_path():
    with pytest.raises(IllegalTransition, match="draft -> commit"):
        move_card(card("draft", tier="T1", parent=None), "commit", by="akp", now=NOW)


def test_empty_string_parent_card_claiming_t1_cannot_use_the_fast_path():
    # `parent: ""` is the same orphan escalation as `parent: None` -- an
    # empty string must not buy the T1 draft -> commit fast path either.
    with pytest.raises(IllegalTransition, match="draft -> commit"):
        move_card(card("draft", tier="T1", parent=""), "commit", by="akp", now=NOW)


def test_unrecognised_tier_does_not_get_the_fast_path():
    # I9: fail closed. An unknown tier is not a licence for the fast lane.
    with pytest.raises(IllegalTransition, match="draft -> commit"):
        move_card(card("draft", tier="t1"), "commit", by="akp", now=NOW)


def test_genuinely_reversible_t1_card_keeps_the_fast_path():
    # The fix must not close the fast lane on the cards it exists for.
    assert move_card(card("draft", tier="T1"), "commit", by="akp", now=NOW).state == "commit"
