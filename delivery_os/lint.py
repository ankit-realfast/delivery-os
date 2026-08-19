from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from delivery_os.card import Card, STATES

T1_REQUIRED = ["intent", "eval", "parent"]
T2_REQUIRED = [
    "intent", "eval", "decider", "value_line", "kill_criterion", "observation_date",
]

T2_TRIGGERS = [
    ("orphan", lambda c: c.parent is None, "card has no parent"),
    ("behaviour-delta", lambda c: c.behaviour_delta != "none", "behaviour delta is not none"),
    ("no-flag", lambda c: not c.flag_off, "cannot be switched off with a flag"),
    ("production-data", lambda c: c.touches_production_data, "changes the shape of production data"),
    ("auth", lambda c: c.touches_auth, "touches auth, permissions, or security posture"),
    ("external-commitment", lambda c: c.external_commitment, "creates an external commitment"),
]


def required_tier(card: Card) -> str:
    return "T2" if any(pred(card) for _, pred, _ in T2_TRIGGERS) else "T1"


@dataclass(frozen=True)
class Finding:
    card_id: str
    rule: str
    message: str


def lint_card(card: Card) -> list[Finding]:
    findings: list[Finding] = []

    if card.state not in STATES:
        findings.append(Finding(card.id, "bad-state", f"unknown state '{card.state}'"))

    if required_tier(card) == "T2" and card.tier != "T2":
        reasons = "; ".join(msg for _, pred, msg in T2_TRIGGERS if pred(card))
        findings.append(Finding(card.id, "tier-escalation", f"must be T2: {reasons}"))

    if card.behaviour_delta != "none" and not card.delta_owner:
        findings.append(
            Finding(card.id, "unowned-delta", "non-zero behaviour delta requires delta_owner")
        )

    required = T2_REQUIRED if card.tier == "T2" else T1_REQUIRED
    for name in required:
        if not getattr(card, name, None):
            findings.append(
                Finding(card.id, "missing-field", f"{card.tier} card requires '{name}'")
            )

    return findings
