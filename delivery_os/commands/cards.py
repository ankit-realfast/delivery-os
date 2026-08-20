from __future__ import annotations

import dataclasses
import re
from importlib import resources
from pathlib import Path
from typing import Any

from delivery_os.card import Card, dump_card
from delivery_os.commands.common import (
    EXIT_FINDINGS,
    EXIT_OK,
    EXIT_USAGE,
    CommandContext,
    atomic_create,
    card_dict,
    emit,
    error,
    find_card_or_error,
    next_states,
)
from delivery_os.lint import (
    T1_REQUIRED,
    T2_REQUIRED,
    effective_tier,
    lint_card,
    lint_corpus,
    tier_reasons,
)

COMMANDS = frozenset({"new", "show", "explain", "status", "lint"})
TEMPLATES = resources.files("delivery_os") / "templates"


def register(subparsers: Any) -> None:
    new = subparsers.add_parser("new", help="draft a card")
    new.add_argument("engagement")
    new.add_argument("title")
    new.add_argument("--tier", default="T1", choices=["T1", "T2"])
    new.add_argument("--parent", default=None)
    new.add_argument("--dry-run", action="store_true")

    show = subparsers.add_parser("show", help="show one card")
    show.add_argument("card_id")
    explain = subparsers.add_parser("explain", help="explain a card's policy and next steps")
    explain.add_argument("card_id")
    subparsers.add_parser("status", help="list current cards")
    subparsers.add_parser("lint", help="validate the card collection")


def _slug(title: str) -> str:
    return re.sub(r"[^\w]+", "-", title.lower()).strip("-_")


def next_card_id(
    root: str | Path,
    additional_roots: tuple[str | Path, ...] = (),
) -> str:
    roots = (root, *additional_roots)
    ids = [
        int(match.group(1))
        for candidate_root in roots
        for path in Path(candidate_root).rglob("C-*.md")
        if (match := re.match(r"C-(\d{4,})(?!\d)", path.name))
    ]
    return f"C-{max(ids, default=0) + 1:04d}"


def new_card(
    root: str | Path,
    engagement: str,
    title: str,
    tier: str,
    parent: str | None,
    *,
    reserved_roots: tuple[str | Path, ...] = (),
    dry_run: bool = False,
) -> tuple[Path, str]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", engagement):
        raise ValueError(
            "engagement must be one safe directory name using letters, numbers, '.', '_' or '-'"
        )
    slug = _slug(title)
    if not slug:
        raise ValueError("title must contain at least one letter or number")
    if parent is None:
        tier = "T2"
    card_id = next_card_id(root, reserved_roots)
    template = (TEMPLATES / f"card-{tier.lower()}.md").read_text(encoding="utf-8")
    safe_title = (
        title.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    body = template.format(id=card_id, title=safe_title, parent=parent or "null")
    path = Path(root) / engagement / f"{card_id}-{slug}.md"
    if not dry_run:
        atomic_create(path, body)
    return path, body


def _explanation(card: Card) -> dict[str, Any]:
    tier = effective_tier(card)
    required = T2_REQUIRED if tier == "T2" else T1_REQUIRED
    missing = [name for name in required if not getattr(card, name, None)]
    return {
        "id": card.id,
        "title": card.title,
        "state": card.state,
        "review_level": "reviewed" if tier == "T2" else "fast",
        "tier": tier,
        "review_reasons": tier_reasons(card),
        "missing_before_review": missing,
        "next_states": next_states(card),
        "blocked_on": card.blocked_on,
    }


def _render_explanation(data: dict[str, Any]) -> str:
    lines = [
        f"{data['id']} — {data['title']}",
        f"State: {data['state']}",
        f"Review level: {data['review_level']} ({data['tier']})",
    ]
    if data["review_reasons"]:
        lines.append("Why reviewed approval is required:")
        lines.extend(f"  - {reason}" for reason in data["review_reasons"])
    if data["missing_before_review"]:
        lines.append("Complete before requesting approval:")
        lines.extend(f"  - {name}" for name in data["missing_before_review"])
    lines.append(
        "Next states: " + (", ".join(data["next_states"]) or "none; this card is finished")
    )
    if data["blocked_on"]:
        lines.append(f"Blocked on: {data['blocked_on']}")
    return "\n".join(lines)


def handle(args: Any, context: CommandContext) -> int:
    if args.cmd == "new":
        if args.parent and find_card_or_error(context, args.parent) is None:
            return EXIT_USAGE
        try:
            path, body = new_card(
                context.root,
                args.engagement,
                args.title,
                args.tier,
                args.parent,
                reserved_roots=(context.config.archive_path,),
                dry_run=args.dry_run,
            )
        except (FileExistsError, OSError, ValueError) as exc:
            error(str(exc), as_json=context.as_json, code="create_failed")
            return EXIT_USAGE
        new_payload = {
            "path": str(path),
            "dry_run": args.dry_run,
            "content": body if args.dry_run else None,
        }
        text = f"Would create {path}" if args.dry_run else f"Created {path}"
        emit(new_payload if context.as_json else text, as_json=context.as_json)
        return EXIT_OK

    if args.cmd == "show":
        card = find_card_or_error(context, args.card_id)
        if card is None:
            return EXIT_USAGE
        emit(
            card_dict(card) if context.as_json else dump_card(card).rstrip(),
            as_json=context.as_json,
        )
        return EXIT_OK

    if args.cmd == "explain":
        card = find_card_or_error(context, args.card_id)
        if card is None:
            return EXIT_USAGE
        explanation_data = _explanation(card)
        emit(
            explanation_data if context.as_json else _render_explanation(explanation_data),
            as_json=context.as_json,
        )
        return EXIT_OK

    if args.cmd == "status":
        status_data = [_explanation(card) | {"path": str(card.path)} for card in context.cards]
        if context.as_json:
            emit({"cards": status_data}, as_json=True)
        elif not status_data:
            emit("No cards yet.", as_json=False)
        else:
            emit(
                "\n".join(
                    f"{item['id']}  {item['state']:<8}  {item['review_level']:<8}  "
                    f"{item['title']}"
                    + (f"  [blocked on {item['blocked_on']}]" if item["blocked_on"] else "")
                    for item in status_data
                ),
                as_json=False,
            )
        return EXIT_OK

    findings = [finding for card in context.cards for finding in lint_card(card)]
    findings += lint_corpus(context.cards, context.config.project_root)
    lint_payload = [dataclasses.asdict(finding) for finding in findings]
    if context.as_json:
        emit({"valid": not findings, "findings": lint_payload}, as_json=True)
    elif findings:
        emit(
            "\n".join(
                f"{finding.path or finding.card_id}"
                f"{f':{finding.line}' if finding.line else ''}: "
                f"{finding.rule}: {finding.message}"
                for finding in findings
            ),
            as_json=False,
        )
    else:
        count = len(context.cards)
        emit(f"OK — {count} card{'s' if count != 1 else ''} valid.", as_json=False)
    return EXIT_FINDINGS if findings else EXIT_OK
