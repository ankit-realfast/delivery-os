from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from delivery_os.card import Card, STATES, state_at_least

TIERS = ("T1", "T2")

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
    """The tier the trigger test derives (spec 4). Ignores what was authored."""
    return "T2" if any(pred(card) for _, pred, _ in T2_TRIGGERS) else "T1"


def effective_tier(card: Card) -> str:
    """The tier that actually governs the card. The one tier every caller uses.

    Spec 3/4: "Tier is derived by the trigger test, never authored." So:

    - Authoring can never de-escalate. A card that derives T2 is T2 whatever
      the frontmatter claims; otherwise authoring `tier: T1` on an
      auth-touching card routes around the OS's only governance gate.
    - Authoring may escalate. Over-tiering is a voluntary choice of the
      stricter lane and is honoured (lint permits it).
    - An unrecognised tier string is treated as T2. An unknown tier is not a
      licence for the fast lane; fail closed.
    """
    if card.tier not in TIERS:
        return "T2"
    return "T2" if required_tier(card) == "T2" else card.tier


@dataclass(frozen=True)
class Finding:
    card_id: str
    rule: str
    message: str


def lint_card(card: Card) -> list[Finding]:
    findings: list[Finding] = []

    if card.state not in STATES:
        findings.append(Finding(card.id, "bad-state", f"unknown state '{card.state}'"))

    if card.tier not in TIERS:
        findings.append(
            Finding(card.id, "bad-tier",
                    f"unknown tier '{card.tier}' (expected one of {', '.join(TIERS)}); "
                    "treated as T2")
        )

    if required_tier(card) == "T2" and card.tier != "T2":
        reasons = "; ".join(msg for _, pred, msg in T2_TRIGGERS if pred(card))
        findings.append(Finding(card.id, "tier-escalation", f"must be T2: {reasons}"))

    if card.behaviour_delta != "none" and not card.delta_owner:
        findings.append(
            Finding(card.id, "unowned-delta", "non-zero behaviour delta requires delta_owner")
        )

    tier = effective_tier(card)
    required = T2_REQUIRED if tier == "T2" else T1_REQUIRED
    for name in required:
        if not getattr(card, name, None):
            findings.append(
                Finding(card.id, "missing-field", f"{tier} card requires '{name}'")
            )

    return findings
