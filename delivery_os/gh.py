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


def transition_for(
    card: Card, merged: bool, approvers: list[str], deciders: dict[str, str]
) -> str | None:
    if card.state != "draft" and card.state != "contest":
        return None

    # T1 has no contest. An open PR does not move it; a merge commits it.
    # Derived tier, never authored (spec 3/4): a card claiming `tier: T1`
    # while touching auth is T2 and must face the Decider.
    if effective_tier(card) == "T1":
        return "commit" if merged and card.state == "draft" else None

    if not merged:
        return "contest" if card.state == "draft" else None

    if card.state == "contest" and decider_approved(card, approvers, deciders):
        return "commit"
    return None
