from __future__ import annotations

import re
from pathlib import Path

import yaml

from delivery_os.card import Card
from delivery_os.lint import effective_tier

CARD_RE = re.compile(r"(C-\d{4})")


def card_ids_in_paths(paths: list[str]) -> list[str]:
    found: list[str] = []
    for raw in paths:
        path = Path(raw)
        if path.suffix != ".md" or "cards" not in path.parts[:-1]:
            continue
        match = CARD_RE.match(path.name)
        if match and match.group(1) not in found:
            found.append(match.group(1))
    return found


def load_deciders(path: str | Path) -> dict[str, str]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def decider_approved(card: Card, approvers: list[str], deciders: dict[str, str]) -> bool:
    if not card.decider:
        return False
    return any(deciders.get(handle) == card.decider for handle in approvers)


PR_EVENTS = ("open", "merged", "abandoned")


def transition_for(
    card: Card, event: str, approvers: list[str], deciders: dict[str, str]
) -> str | None:
    """The card state a PR event implies, or None for "write nothing".

    `event` is a three-valued domain, not a merged flag. The flag shared the
    lossy encoding that caused C5: `closed` fires for merge *and* for
    abandonment, and `merged=False` cannot tell an open PR from an
    abandoned one, so an abandoned throwaway PR dragged a draft into
    contest, started an M1 clock that grew without bound, and printed
    "waiting {hours}h on {decider}" -- naming a client-side individual for
    a decision never put to them, in a report Schedule A gives commercial
    force.

    "abandoned" returns None unconditionally, before any state inspection.
    Nothing is reversed because nothing should have been written: an
    abandoned PR means the contest never happened. A contest -> draft
    reversal is deliberately NOT used -- transition_for cannot know which
    PR moved a card to contest, so a throwaway PR touching the same file
    would erase genuine client latency from M1 and hand anyone a one-click
    way to zero an inconvenient contractual meter.
    """
    if event not in PR_EVENTS:
        raise ValueError(f"unknown PR event {event!r}; expected one of {PR_EVENTS}")

    if event == "abandoned":
        return None

    if card.state != "draft" and card.state != "contest":
        return None

    # T1 has no contest. An open PR does not move it; a merge commits it.
    # Derived tier, never authored (spec 3/4): a card claiming `tier: T1`
    # while touching auth is T2 and must face the Decider.
    if effective_tier(card) == "T1":
        return "commit" if event == "merged" and card.state == "draft" else None

    if event == "open":
        return "contest" if card.state == "draft" else None

    if card.state == "contest" and decider_approved(card, approvers, deciders):
        return "commit"
    return None
