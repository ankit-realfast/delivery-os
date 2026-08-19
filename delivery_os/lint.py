from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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

    # Spec 4 requires T2's full field set at CONTEST, not at draft: "T2 --
    # irreversible. All seven fields, named Decider signs" is what precedes
    # the build, and drafting is explicitly cheap ("agents draft"). Linting
    # required fields from draft meant `dos new` emitted a card that
    # immediately failed `dos lint`, and cards.yml fails CI on any finding --
    # so a draft card could not live in the repo at all, though card-sync
    # presumes it does. Tier-escalation and the structural checks above
    # apply from draft onward and are unaffected.
    tier = effective_tier(card)
    if state_at_least(card.state, "contest"):
        required = T2_REQUIRED if tier == "T2" else T1_REQUIRED
        for name in required:
            if not getattr(card, name, None):
                findings.append(
                    Finding(card.id, "missing-field", f"{tier} card requires '{name}'")
                )

    return findings


def lint_corpus(cards: list[Card], repo_root: str | Path = ".") -> list[Finding]:
    """Checks that need the whole corpus, or the filesystem, to answer.

    lint_card is deliberately pure -- one card, no I/O. These are the rules
    a single card cannot see.

    I2. Spec 3 rests traceability on the parent link: "That single rule
    guarantees every piece of work in the system traces upward to a stated
    value line and a named Decider." A `parent: C-9999` pointing at nothing,
    and two files claiming the same id, both linted clean and exited 0.

    I3. Rule 1 -- "if you cannot write the eval, you do not have a spec, you
    have a wish" -- was enforced only as string non-emptiness, so
    `eval: "make it smarter"` linted clean and reached commit. A card at
    commit or later must have an eval that resolves to a file that exists.

    What this does NOT verify, and cannot statically: that the pytest node
    id after `::` exists inside that file (resolving it means importing and
    collecting the module, which runs the eval's import side effects during
    a lint), and that the eval actually tests the card's intent. The second
    is human judgment the spec reserves for humans (section 5: "judging
    whether an eval reflects what the business actually cares about").
    `dos verify` closes the first gap at the point it matters -- a node id
    that does not exist now returns "error", never a recorded red (C1).
    """
    findings: list[Finding] = []

    by_id: dict[str, list[str]] = {}
    for card in cards:
        by_id.setdefault(card.id, []).append(str(card.path) if card.path else "<memory>")

    for card_id, paths in by_id.items():
        if len(paths) > 1:
            findings.append(Finding(
                card_id, "duplicate-id",
                f"{len(paths)} files claim this id: {', '.join(sorted(paths))}",
            ))

    for card in cards:
        if card.parent and card.parent not in by_id:
            findings.append(Finding(
                card.id, "dangling-parent",
                f"parent '{card.parent}' is not a card in this corpus",
            ))

    root = Path(repo_root)
    for card in cards:
        if not card.eval or not state_at_least(card.state, "commit"):
            continue
        target = card.eval.split("::", 1)[0]
        if not (root / target).exists():
            findings.append(Finding(
                card.id, "unresolvable-eval",
                f"eval '{card.eval}' does not resolve to a file under {root}: "
                "rule 1 says a card you cannot test is a wish, not a spec",
            ))

    return findings
