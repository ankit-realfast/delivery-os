from datetime import date

from delivery_os.card import Card
from delivery_os.lint import Finding, lint_card


def t1(**kw) -> Card:
    base = dict(
        id="C-0002", title="t", tier="T1", state="contest", parent="C-0001",
        eval="evals/C-0002_test.py::test_x",
        intent="something is true",
    )
    base.update(kw)
    return Card(**base)


def t2(**kw) -> Card:
    base = dict(
        id="C-0001", title="t", tier="T2", state="contest", parent=None,
        decider="Priya Raman", eval="evals/C-0001_test.py::test_x",
        value_line="tickets: 40/mo -> 5/mo", kill_criterion="baseline under 20",
        observation_date=date(2026, 9, 30), touches_production_data=True,
        intent="something is true",
    )
    base.update(kw)
    return Card(**base)


def rules(findings: list[Finding]) -> set[str]:
    return {f.rule for f in findings}


def test_complete_t1_card_is_clean():
    assert lint_card(t1()) == []


def test_complete_t2_card_is_clean():
    assert lint_card(t2()) == []


def test_t1_without_eval_is_a_wish_not_a_spec():
    findings = lint_card(t1(eval=None))
    assert "missing-field" in rules(findings)
    assert any("eval" in f.message for f in findings)


def test_t1_without_intent_is_rejected():
    assert "missing-field" in rules(lint_card(t1(intent="")))


def test_t1_with_empty_blocked_on_is_fine():
    assert lint_card(t1(blocked_on=None)) == []


def test_t2_missing_kill_criterion_is_rejected():
    findings = lint_card(t2(kill_criterion=None))
    assert any("kill_criterion" in f.message for f in findings)


def test_t2_missing_observation_date_is_rejected():
    findings = lint_card(t2(observation_date=None))
    assert any("observation_date" in f.message for f in findings)


def test_t2_missing_value_line_is_rejected():
    findings = lint_card(t2(value_line=None))
    assert any("value_line" in f.message for f in findings)


def test_unknown_state_is_rejected():
    assert "bad-state" in rules(lint_card(t1(state="in_progress")))


def test_t1_missing_parent_is_escalated_to_t2_not_asked_for_a_parent():
    # DELIBERATE UPDATE. Spec rule 2: "A card with no parent is T2 by
    # definition." So a parentless card is not a T1 missing a field -- it is
    # a T2, and T2 cards have no parent. Demanding `parent` of it was the old
    # authored-tier model leaking through. What must fire is tier-escalation
    # plus the T2 field set.
    findings = lint_card(t1(parent=None))
    escalation = next(f for f in findings if f.rule == "tier-escalation")
    assert "no parent" in escalation.message
    missing = {f.message for f in findings if f.rule == "missing-field"}
    assert any("decider" in m for m in missing)
    assert all(m.startswith("T2 card") for m in missing)


def test_under_tiered_auth_card_is_linted_against_the_t2_field_set():
    # C4: tier is derived, never authored. Authoring `tier: T1` on an
    # auth-touching card must not buy the T1 (three-field) lint.
    findings = lint_card(t1(touches_auth=True))
    assert "tier-escalation" in rules(findings)
    missing = {f.message for f in findings if f.rule == "missing-field"}
    assert any("kill_criterion" in m for m in missing)


def test_over_tiering_still_gets_the_strict_field_set():
    # Authoring may escalate; effective_tier honours it.
    findings = lint_card(t1(tier="T2"))
    assert "tier-escalation" not in rules(findings)
    assert any("kill_criterion" in f.message for f in findings if f.rule == "missing-field")


def test_unrecognised_tier_is_a_finding_and_routes_to_the_strict_lane():
    # I9: lint used to treat an unknown tier as T1, gh as T2, and the
    # scoreboard silently excluded it.
    findings = lint_card(t1(tier="t2"))
    assert "bad-tier" in rules(findings)
    assert any("kill_criterion" in f.message for f in findings if f.rule == "missing-field")


# --- I6: required fields are demanded from contest onward, not from draft ---

def test_an_empty_draft_card_lints_clean():
    # Spec 4: T2's full field set is required at contest, not at draft.
    # `dos new` used to emit a card that immediately failed `dos lint`, and
    # cards.yml fails CI on any finding -- so a draft card could not live in
    # the repo, though card-sync presumes it does.
    assert lint_card(t2(state="draft", decider=None, eval=None, value_line=None,
                        kill_criterion=None, observation_date=None)) == []


def test_a_bare_t1_draft_lints_clean():
    assert lint_card(t1(state="draft", eval=None, intent="")) == []


def test_the_same_card_at_contest_is_rejected():
    # The discriminator: draft is exempt, contest is not.
    findings = lint_card(t2(state="contest", decider=None, eval=None,
                            value_line=None, kill_criterion=None,
                            observation_date=None))
    assert {f.rule for f in findings} == {"missing-field"}
    assert {"eval", "decider", "value_line", "kill_criterion", "observation_date"} == {
        f.message.split("'")[1] for f in findings
    }


def test_structural_checks_still_apply_to_a_draft():
    # Tier escalation and delta ownership are not deferred to contest.
    findings = lint_card(t1(state="draft", touches_auth=True))
    assert "tier-escalation" in rules(findings)
    assert lint_card(t1(state="draft", tier="t9")) != []


def test_a_card_at_commit_is_still_checked():
    assert "missing-field" in rules(lint_card(t1(state="commit", eval=None)))
