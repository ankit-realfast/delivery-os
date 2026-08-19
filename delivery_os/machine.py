from __future__ import annotations

import dataclasses
from datetime import datetime

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


class IllegalTransition(Exception):
    pass


def move_card(card: Card, to_state: str, by: str, now: datetime) -> Card:
    legal = list(LEGAL_TRANSITIONS.get(card.state, []))
    # spec 4: T1 has no contest. Tier is *derived*, never authored -- an
    # under-tiered card must not buy the fast lane by claiming `tier: T1`.
    if effective_tier(card) == "T1" and card.state == "draft":
        legal.append("commit")
    if to_state not in legal:
        raise IllegalTransition(f"{card.state} -> {to_state}")
    entry = {"state": to_state, "at": now.isoformat(), "by": by}
    return dataclasses.replace(
        card, state=to_state, history=[*card.history, entry]
    )


def record_verify(card: Card, passed: bool, by: str, now: datetime) -> Card:
    entry = {
        "state": card.state,
        "at": now.isoformat(),
        "by": by,
        "verify": "pass" if passed else "fail",
    }
    return dataclasses.replace(card, history=[*card.history, entry])
