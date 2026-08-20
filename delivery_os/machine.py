from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any

from delivery_os.card import Card
from delivery_os.lint import effective_tier

LEGAL_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["contest"],
    "contest": ["commit", "draft"],
    "commit": ["build"],
    "build": ["verify"],
    # The red-eval fork: build wrong -> build; spec wrong -> contest.
    "verify": ["observe", "build", "contest"],
    "observe": ["closed"],
    "closed": [],
}


# History keys that annotate a card in place rather than record a state
# change. M1 must not read these as transitions: an observation recorded
# while a card sits at `commit` would otherwise overwrite the commit
# timestamp and inflate decision latency.
ANNOTATION_KEYS = ("verify", "observed")


class IllegalTransition(Exception):
    pass


def move_card(
    card: Card,
    to_state: str,
    by: str,
    now: datetime,
    metadata: dict[str, Any] | None = None,
) -> Card:
    legal = list(LEGAL_TRANSITIONS.get(card.state, []))
    # spec 4: T1 has no contest. Tier is *derived*, never authored -- an
    # under-tiered card must not buy the fast lane by claiming `tier: T1`.
    if effective_tier(card) == "T1" and card.state == "draft":
        legal.append("commit")
    if to_state not in legal:
        raise IllegalTransition(f"{card.state} -> {to_state}")
    if to_state == "closed" and (card.value_moved is None or card.delta_held is None):
        raise IllegalTransition(
            "observe -> closed requires both business value and behaviour outcomes; "
            "run 'dos observe' first"
        )
    entry = {"state": to_state, "at": now.isoformat(), "by": by}
    if metadata:
        entry.update(metadata)
    return dataclasses.replace(card, state=to_state, history=[*card.history, entry])


def record_verify(
    card: Card,
    passed: bool,
    by: str,
    now: datetime,
    *,
    command: list[str] | None = None,
    exit_code: int | None = None,
    duration_seconds: float | None = None,
) -> Card:
    entry: dict[str, Any] = {
        "state": card.state,
        "at": now.isoformat(),
        "by": by,
        "verify": "pass" if passed else "fail",
    }
    if command is not None:
        entry["command"] = command
    if exit_code is not None:
        entry["exit_code"] = exit_code
    if duration_seconds is not None:
        entry["duration_seconds"] = duration_seconds
    return dataclasses.replace(card, history=[*card.history, entry])


def record_observation(
    card: Card, value_moved: bool, delta_held: bool, by: str, now: datetime
) -> Card:
    """Answer the two observation-date questions against what the card claimed.

    Spec 4: "On that date, two questions are answered against what the card
    claimed: did the value line move, and was the behaviour delta what was
    declared?" value_moved feeds the scoreboard; delta_held is what makes
    M3's stated guard implementable.
    """
    entry = {
        "state": card.state,
        "at": now.isoformat(),
        "by": by,
        "observed": "moved" if value_moved else "not-moved",
        "delta": "held" if delta_held else "broken",
    }
    return dataclasses.replace(
        card,
        value_moved=value_moved,
        delta_held=delta_held,
        history=[*card.history, entry],
    )


def record_approval(
    card: Card,
    *,
    approved_by: str,
    recorded_by: str,
    evidence: str,
    now: datetime,
) -> Card:
    """Commit a contested card with an auditable external approval reference."""
    if card.state != "contest":
        raise IllegalTransition(f"{card.state} -> commit by approval")
    if not card.decider:
        raise IllegalTransition("approval requires a named decider on the card")
    if approved_by != card.decider:
        raise IllegalTransition(
            f"approval is from {approved_by!r}, but the named decider is {card.decider!r}"
        )
    if not evidence.strip():
        raise IllegalTransition("approval requires a non-empty evidence reference")
    return move_card(
        card,
        "commit",
        by=recorded_by,
        now=now,
        metadata={"approved_by": approved_by, "approval_evidence": evidence.strip()},
    )
