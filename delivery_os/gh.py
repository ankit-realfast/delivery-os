from __future__ import annotations

import re
from pathlib import Path

import yaml

from delivery_os.card import Card
from delivery_os.lint import effective_tier

# Anchored at the start of a filename by .match(), and closed on the right
# by a negative lookahead. Without it "C-00071-x.md" matched as C-0007 and
# card-sync wrote state to a DIFFERENT card (deferred #9).
CARD_RE = re.compile(r"(C-\d{4,})(?!\d)")


def card_ids_in_paths(paths: list[str], root: str | Path = "cards") -> list[str]:
    """Card ids named by changed paths that lie under the corpus root.

    `root` is threaded from --root: the literal "cards" was hardcoded here
    while the loader honoured --root, so any non-default root made `sync-pr`
    silently match nothing (I12).
    """
    root_parts = tuple(part for part in Path(root).parts if part != ".")
    found: list[str] = []
    for raw in paths:
        path = Path(raw)
        if path.suffix != ".md":
            continue
        parts = path.parts
        if len(parts) <= len(root_parts) or parts[: len(root_parts)] != root_parts:
            continue
        match = CARD_RE.match(path.name)
        if match and match.group(1) not in found:
            found.append(match.group(1))
    return found


def load_deciders(path: str | Path) -> dict[str, str]:
    loaded = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict) or not all(
        isinstance(handle, str) and isinstance(decider, str) for handle, decider in loaded.items()
    ):
        raise ValueError(f"{path}: deciders must map GitHub usernames to decider text")
    return loaded


def decider_approved(card: Card, approvers: list[str], deciders: dict[str, str]) -> bool:
    if not card.decider:
        return False
    return any(deciders.get(handle) == card.decider for handle in approvers)


PR_EVENTS = ("open", "merged", "abandoned")


def transition_for(
    card: Card,
    event: str,
    approvers: list[str],
    deciders: dict[str, str],
    pull_request: str | None = None,
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

    Contest history now carries the pull-request number. An abandoned event
    may therefore reverse contest -> draft only when the latest transition
    was written by that same PR. A throwaway PR cannot erase a decision
    started elsewhere.
    """
    if event not in PR_EVENTS:
        raise ValueError(f"unknown PR event {event!r}; expected one of {PR_EVENTS}")

    if event == "abandoned":
        # Reverse only the contest started by this same pull request. This
        # preserves a genuine decision raised elsewhere while preventing an
        # abandoned proposal from leaving an M1 clock running forever.
        latest_transition = next(
            (
                entry
                for entry in reversed(card.history)
                if "verify" not in entry and "observed" not in entry
            ),
            None,
        )
        if (
            card.state == "contest"
            and pull_request
            and latest_transition
            and latest_transition.get("state") == "contest"
            and latest_transition.get("pull_request") == pull_request
        ):
            return "draft"
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

    # event == "merged".
    if card.state == "draft":
        # C3: a T2 card ADDED by this PR is still `draft` when the PR merges,
        # because no earlier event ever saw it. Falling through to None left
        # it with no contest history ever, permanently invisible to
        # compute_m1 -- the meter Schedule A makes contractual.
        #
        # It becomes "contest", not "commit". Spec 4 puts contest between
        # draft and commit for T2 and machine.LEGAL_TRANSITIONS refuses
        # draft -> commit, so a T2 card may not reach commit without a
        # recorded contest. Committing here even when the Decider approved
        # the PR would record a zero-length contest and let the supplier
        # make its own contractual meter read zero -- the anti-pattern C5
        # exists to prevent. The Decider commits it explicitly.
        return "contest"

    if card.state == "contest" and decider_approved(card, approvers, deciders):
        return "commit"
    return None
