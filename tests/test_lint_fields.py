from datetime import date

from delivery_os.card import Card
from delivery_os.lint import Finding, lint_card


def t1(**kw) -> Card:
    base = dict(
        id="C-0002", title="t", tier="T1", state="draft", parent="C-0001",
        eval="evals/C-0002_test.py::test_x",
        intent="something is true",
    )
    base.update(kw)
    return Card(**base)


def t2(**kw) -> Card:
    base = dict(
        id="C-0001", title="t", tier="T2", state="draft", parent=None,
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
