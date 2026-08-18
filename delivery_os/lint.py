from __future__ import annotations

from dataclasses import dataclass

from delivery_os.card import Card, STATES

T1_REQUIRED = ["intent", "eval", "parent"]
T2_REQUIRED = [
    "intent", "eval", "decider", "value_line", "kill_criterion", "observation_date",
]


@dataclass(frozen=True)
class Finding:
    card_id: str
    rule: str
    message: str


def lint_card(card: Card) -> list[Finding]:
    findings: list[Finding] = []

    if card.state not in STATES:
        findings.append(Finding(card.id, "bad-state", f"unknown state '{card.state}'"))

    required = T2_REQUIRED if card.tier == "T2" else T1_REQUIRED
    for name in required:
        if not getattr(card, name, None):
            findings.append(
                Finding(card.id, "missing-field", f"{card.tier} card requires '{name}'")
            )

    return findings
