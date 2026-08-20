from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from delivery_os.commands.common import (
    EXIT_OK,
    EXIT_USAGE,
    CommandContext,
    emit,
    error,
    find_card,
    write_or_conflict,
)
from delivery_os.gh import PR_EVENTS, card_ids_in_paths, load_deciders, transition_for
from delivery_os.machine import move_card

COMMANDS = frozenset({"sync-pr"})


def register(subparsers: Any) -> None:
    sync = subparsers.add_parser("sync-pr", help="apply a pull-request event (automation command)")
    sync.add_argument("--changed", required=True)
    sync.add_argument("--approvers", default="")
    sync.add_argument("--pr-state", required=True, choices=PR_EVENTS)
    sync.add_argument("--deciders", default=None)
    sync.add_argument("--pr", default=None, help="pull-request number for audit history")


def handle(args: Any, context: CommandContext) -> int:
    changed = [path.strip() for path in re.split(r"[,\n]", args.changed) if path.strip()]
    approvers = [name.strip() for name in args.approvers.split(",") if name.strip()]
    deciders_path = Path(args.deciders).resolve() if args.deciders else context.config.deciders_path
    try:
        deciders = load_deciders(deciders_path)
    except (ValueError, OSError) as exc:
        error(f"Cannot load deciders: {exc}", as_json=context.as_json, code="deciders_error")
        return EXIT_USAGE
    try:
        sync_root: str | Path = context.root.relative_to(context.config.project_root)
    except ValueError:
        sync_root = context.root
    wanted = card_ids_in_paths(changed, sync_root)
    transitions: list[dict[str, Any]] = []
    for card_id in wanted:
        card = find_card(context.cards, card_id)
        if card is None:
            transitions.append({"id": card_id, "transition": None, "reason": "not found"})
            continue
        next_state = transition_for(
            card,
            args.pr_state,
            approvers,
            deciders,
            pull_request=args.pr,
        )
        if next_state is None:
            transitions.append({"id": card_id, "transition": None, "reason": "policy denied"})
            continue
        metadata: dict[str, Any] = {}
        if args.pr:
            metadata["pull_request"] = args.pr
        if next_state == "commit":
            metadata.update(
                {
                    "approved_by": card.decider,
                    "approval_evidence": f"github:pull/{args.pr or 'unknown'}",
                    "approving_handles": approvers,
                }
            )
        moved = move_card(
            card,
            next_state,
            by="github",
            now=datetime.now(UTC),
            metadata=metadata or None,
        )
        code = write_or_conflict(moved, as_json=context.as_json)
        if code:
            return code
        transitions.append({"id": card_id, "from": card.state, "transition": next_state})
    if context.as_json:
        emit({"transitions": transitions}, as_json=True)
    else:
        emit(
            "\n".join(
                f"{item['id']} -> {item['transition']}"
                if item.get("transition")
                else f"{item['id']}: no transition ({item['reason']})"
                for item in transitions
            )
            or "No changed card paths found.",
            as_json=False,
        )
    return EXIT_OK
