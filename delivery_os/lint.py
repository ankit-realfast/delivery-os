from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from delivery_os.card import CURRENT_SCHEMA_VERSION, STATES, Card, state_at_least

TIERS = ("T1", "T2")

T1_REQUIRED = ["intent", "eval"]
T2_REQUIRED = [
    "intent",
    "eval",
    "decider",
    "value_line",
    "kill_criterion",
    "observation_date",
]

T2_TRIGGERS = [
    # Falsiness, not `is None`: spec 3 says "a card with no parent is T2 by
    # definition", and `parent: ""` is no parent. Testing identity against
    # None let an empty string route around the gate -- `required_tier`
    # stayed T1, `move_card` granted the draft -> commit fast path, and
    # `transition_for` committed a merge with no named Decider.
    ("orphan", lambda c: not c.parent, "card has no parent"),
    ("behaviour-delta", lambda c: c.behaviour_delta != "none", "behaviour delta is not none"),
    ("no-flag", lambda c: not c.flag_off, "cannot be switched off with a flag"),
    (
        "production-data",
        lambda c: c.touches_production_data,
        "changes the shape of production data",
    ),
    ("auth", lambda c: c.touches_auth, "touches auth, permissions, or security posture"),
    ("external-commitment", lambda c: c.external_commitment, "creates an external commitment"),
]


def required_tier(card: Card) -> str:
    """The tier the trigger test derives (spec 4). Ignores what was authored."""
    return "T2" if any(pred(card) for _, pred, _ in T2_TRIGGERS) else "T1"


def tier_reasons(card: Card) -> list[str]:
    """Plain-language reasons the card requires reviewed approval."""
    return [message for _, predicate, message in T2_TRIGGERS if predicate(card)]


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
    path: str | None = None
    line: int | None = None


def lint_card(card: Card) -> list[Finding]:
    findings: list[Finding] = []
    path = str(card.path) if card.path else None

    def line_for(field: str) -> int:
        return card.field_lines.get(field, 1)

    if card.schema_version != CURRENT_SCHEMA_VERSION:
        findings.append(
            Finding(
                card.id,
                "legacy-schema",
                f"schema version {card.schema_version} must be migrated to "
                f"{CURRENT_SCHEMA_VERSION} with 'dos migrate'",
                path,
                line_for("schema_version"),
            )
        )

    if isinstance(card.eval, str):
        findings.append(
            Finding(
                card.id,
                "legacy-eval-format",
                "pytest-path evals must be migrated to a language-neutral command mapping",
                path,
                line_for("eval"),
            )
        )

    if card.state not in STATES:
        findings.append(
            Finding(
                card.id,
                "bad-state",
                f"unknown state '{card.state}'",
                path,
                line_for("state"),
            )
        )

    if not re.fullmatch(r"C-\d{4,}", card.id):
        findings.append(
            Finding(
                card.id,
                "bad-id",
                "id must look like C-0001 and contain at least four digits",
                path,
                line_for("id"),
            )
        )

    if card.tier not in TIERS:
        findings.append(
            Finding(
                card.id,
                "bad-tier",
                f"unknown tier '{card.tier}' (expected one of {', '.join(TIERS)}); treated as T2",
                path,
                line_for("tier"),
            )
        )

    if required_tier(card) == "T2" and card.tier != "T2":
        reasons = "; ".join(tier_reasons(card))
        findings.append(
            Finding(
                card.id,
                "tier-escalation",
                f"reviewed approval required because: {reasons}",
                path,
                line_for("tier"),
            )
        )

    if card.behaviour_delta != "none" and not card.delta_owner:
        findings.append(
            Finding(
                card.id,
                "unowned-delta",
                "a user-visible behaviour change requires delta_owner",
                path,
                line_for("delta_owner"),
            )
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
                    Finding(
                        card.id,
                        "missing-field",
                        f"{tier} card requires '{name}'",
                        path,
                        line_for(name),
                    )
                )

    if card.state == "closed" and (card.value_moved is None or card.delta_held is None):
        findings.append(
            Finding(
                card.id,
                "closed-without-outcome",
                "closed cards must record both value_moved and delta_held",
                path,
                line_for("state"),
            )
        )

    if card.path and not card.path.name.startswith(f"{card.id}-"):
        findings.append(
            Finding(
                card.id,
                "filename-id-mismatch",
                f"filename must start with '{card.id}-'",
                path,
            )
        )

    previous_time: datetime | None = None
    transition_entries = [
        entry for entry in card.history if "verify" not in entry and "observed" not in entry
    ]
    previous_state = "draft"
    transition_map = {
        "draft": {"contest"} | ({"commit"} if effective_tier(card) == "T1" else set()),
        "contest": {"commit", "draft"},
        "commit": {"build"},
        "build": {"verify"},
        "verify": {"observe", "build", "contest"},
        "observe": {"closed"},
        "closed": set(),
    }
    for index, entry in enumerate(transition_entries):
        next_state = entry.get("state")
        is_initial_draft = index == 0 and previous_state == "draft" and next_state == "draft"
        if not is_initial_draft and next_state not in transition_map.get(previous_state, set()):
            findings.append(
                Finding(
                    card.id,
                    "illegal-history-transition",
                    f"history transition {index} is {previous_state} -> {next_state}",
                    path,
                )
            )
        if isinstance(next_state, str):
            previous_state = next_state
    for index, entry in enumerate(card.history):
        stamp = datetime.fromisoformat(entry["at"])
        if previous_time and stamp < previous_time:
            findings.append(
                Finding(
                    card.id,
                    "history-out-of-order",
                    f"history entry {index} is earlier than the entry before it",
                    path,
                )
            )
        previous_time = stamp
        if entry.get("verify") not in {None, "pass", "fail"}:
            findings.append(
                Finding(
                    card.id,
                    "bad-verification-history",
                    f"history entry {index} has unknown verify outcome {entry.get('verify')!r}",
                    path,
                )
            )

    if transition_entries and transition_entries[-1].get("state") != card.state:
        findings.append(
            Finding(
                card.id,
                "state-history-mismatch",
                f"card says state {card.state!r}, but its last transition says "
                f"{transition_entries[-1].get('state')!r}",
                path,
            )
        )

    if (
        card.schema_version == CURRENT_SCHEMA_VERSION
        and effective_tier(card) == "T2"
        and state_at_least(card.state, "commit")
    ):
        commits = [entry for entry in transition_entries if entry.get("state") == "commit"]
        if (
            not commits
            or not commits[-1].get("approved_by")
            or not commits[-1].get("approval_evidence")
        ):
            findings.append(
                Finding(
                    card.id,
                    "missing-approval-evidence",
                    "reviewed cards at commit or later require approved_by and approval_evidence "
                    "in their commit history entry",
                    path,
                )
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
            findings.append(
                Finding(
                    card_id,
                    "duplicate-id",
                    f"{len(paths)} files claim this id: {', '.join(sorted(paths))}",
                    sorted(paths)[0],
                )
            )

    for card in cards:
        if card.parent and card.parent not in by_id:
            findings.append(
                Finding(
                    card.id,
                    "dangling-parent",
                    f"parent '{card.parent}' is not a card in this corpus",
                    str(card.path) if card.path else None,
                )
            )

    parent_by_id = {card.id: card.parent for card in cards}
    reported_cycles: set[tuple[str, ...]] = set()
    for card in cards:
        chain: list[str] = []
        current: str | None = card.id
        while current and current in parent_by_id:
            if current in chain:
                cycle = chain[chain.index(current) :] + [current]
                canonical = tuple(sorted(set(cycle)))
                if canonical not in reported_cycles:
                    reported_cycles.add(canonical)
                    findings.append(
                        Finding(
                            card.id,
                            "parent-cycle",
                            "parent links form a cycle: " + " -> ".join(cycle),
                            str(card.path) if card.path else None,
                        )
                    )
                break
            chain.append(current)
            current = parent_by_id[current]

    root = Path(repo_root)
    for card in cards:
        if not card.eval or not state_at_least(card.state, "commit"):
            continue
        if not isinstance(card.eval, str):
            continue
        target = card.eval.split("::", 1)[0]
        if not (root / target).exists():
            findings.append(
                Finding(
                    card.id,
                    "unresolvable-eval",
                    f"eval '{card.eval}' does not resolve to a file under {root}: "
                    "rule 1 says a card you cannot test is a wish, not a spec",
                    str(card.path) if card.path else None,
                )
            )

    return findings
