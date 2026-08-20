from delivery_os.card import Card
from delivery_os.lint import lint_card, required_tier


def card(**kw) -> Card:
    base = dict(
        id="C-0002", title="t", tier="T1", state="draft", parent="C-0001",
        eval="evals/C-0002_test.py::test_x",
    )
    base.update(kw)
    return Card(intent="something is true", **base)


def rules(findings) -> set[str]:
    return {f.rule for f in findings}


def test_plain_reversible_card_stays_t1():
    assert required_tier(card()) == "T1"


def test_orphan_card_is_t2_by_definition():
    assert required_tier(card(parent=None)) == "T2"
    assert "tier-escalation" in rules(lint_card(card(parent=None)))


def test_empty_string_parent_is_orphan_too_not_a_stated_parent():
    # Finding 2: the orphan trigger tested `c.parent is None`, not
    # falsiness, so `parent: ""` was not caught -- required_tier stayed T1
    # and the card never faced the escalation. Spec: "a card with no parent
    # is T2 by definition"; an empty string is no parent.
    assert required_tier(card(parent="")) == "T2"
    assert "tier-escalation" in rules(lint_card(card(parent="")))


def test_nonzero_behaviour_delta_forces_t2():
    c = card(behaviour_delta="ops team stops using the old sheet", delta_owner="Sam")
    assert required_tier(c) == "T2"


def test_unflaggable_card_forces_t2():
    assert required_tier(card(flag_off=False)) == "T2"


def test_production_data_shape_forces_t2():
    assert required_tier(card(touches_production_data=True)) == "T2"


def test_auth_forces_t2():
    assert required_tier(card(touches_auth=True)) == "T2"


def test_external_commitment_forces_t2():
    assert required_tier(card(external_commitment=True)) == "T2"


def test_escalation_message_names_every_reason():
    findings = lint_card(card(parent=None, touches_auth=True))
    msg = next(f.message for f in findings if f.rule == "tier-escalation")
    assert "no parent" in msg
    assert "auth" in msg


def test_over_tiering_is_allowed():
    c = card(tier="T2", parent="C-0001", decider="P", value_line="v",
             kill_criterion="k", observation_date="2026-09-30")
    assert "tier-escalation" not in rules(lint_card(c))


def test_nonzero_delta_without_owner_is_flagged():
    c = card(tier="T2", parent="C-0001", decider="P", value_line="v",
             kill_criterion="k", observation_date="2026-09-30",
             behaviour_delta="ops team stops using the old sheet")
    assert "unowned-delta" in rules(lint_card(c))
