from __future__ import annotations

import getpass
import os
import shlex
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from delivery_os.card import CURRENT_SCHEMA_VERSION, Card, load_all, migrate_card
from delivery_os.commands.common import (
    EXIT_CONFLICT,
    EXIT_EVAL_ERROR,
    EXIT_FINDINGS,
    EXIT_OK,
    EXIT_USAGE,
    CommandContext,
    emit,
    error,
    find_card,
    find_card_or_error,
    next_states,
    write_or_conflict,
)
from delivery_os.eval_runner import EvalResult, plan_eval, run_eval
from delivery_os.lint import effective_tier, lint_card
from delivery_os.machine import (
    IllegalTransition,
    move_card,
    record_approval,
    record_observation,
    record_verify,
)

COMMANDS = frozenset({"move", "approve", "verify", "observe", "migrate", "archive", "restore"})


def register(subparsers: Any) -> None:
    move = subparsers.add_parser("move", help="move a card to another state")
    move.add_argument("card_id")
    move.add_argument("to_state")
    move.add_argument("--by", required=True)
    move.add_argument("--dry-run", action="store_true")

    approve = subparsers.add_parser("approve", help="record approval from the named decision-maker")
    approve.add_argument("card_id")
    approve.add_argument("--approved-by", required=True)
    approve.add_argument("--recorded-by", required=True)
    approve.add_argument("--evidence", required=True, help="URL, ticket, or meeting-note reference")
    approve.add_argument("--dry-run", action="store_true")

    verify = subparsers.add_parser("verify", help="run and record a card's acceptance command")
    verify.add_argument("card_id")
    verify.add_argument("--by", default=getpass.getuser())
    verify.add_argument("--dry-run", action="store_true")
    verify.add_argument("--no-record", action="store_true", help="run without changing history")

    observe = subparsers.add_parser("observe", help="record business and behaviour outcomes")
    observe.add_argument("card_id")
    observe.add_argument("--by", required=True)
    moved = observe.add_mutually_exclusive_group(required=True)
    moved.add_argument("--moved", dest="value_moved", action="store_true")
    moved.add_argument("--not-moved", dest="value_moved", action="store_false")
    delta = observe.add_mutually_exclusive_group(required=True)
    delta.add_argument("--delta-held", dest="delta_held", action="store_true")
    delta.add_argument("--delta-broken", dest="delta_held", action="store_false")
    observe.add_argument("--dry-run", action="store_true")

    migrate = subparsers.add_parser("migrate", help="upgrade legacy cards to the current schema")
    migrate.add_argument("card_id", nargs="?")
    migrate.add_argument("--dry-run", action="store_true")

    archive = subparsers.add_parser(
        "archive", help="move a closed, unreferenced card to the archive"
    )
    archive.add_argument("card_id")
    archive.add_argument("--yes", action="store_true", help="confirm the archive operation")
    archive.add_argument("--dry-run", action="store_true")

    restore = subparsers.add_parser("restore", help="restore a card from the archive")
    restore.add_argument("card_id")
    restore.add_argument("--yes", action="store_true", help="confirm the restore operation")
    restore.add_argument("--dry-run", action="store_true")


def verify_card(
    card: Card,
    repo_root: str | Path = ".",
    *,
    timeout_seconds: int = 300,
    allowed_environment: tuple[str, ...] = (),
) -> tuple[str, str, str]:
    """Compatibility wrapper around the language-neutral eval runtime."""
    try:
        plan = plan_eval(
            card,
            repo_root,
            default_timeout_seconds=timeout_seconds,
            allowed_environment=allowed_environment,
        )
    except ValueError as exc:
        return "error", "", str(exc)
    result = run_eval(plan)
    outcome = "error" if result.outcome == "timeout" else result.outcome
    return outcome, result.stdout, result.stderr


def _move_without_overwrite(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.link(source, destination)
    try:
        source.unlink()
    except OSError:
        destination.unlink(missing_ok=True)
        raise


def handle(args: Any, context: CommandContext) -> int:
    if args.cmd == "move":
        card = find_card_or_error(context, args.card_id)
        if card is None:
            return EXIT_USAGE
        if card.state == "contest" and args.to_state == "commit" and effective_tier(card) == "T2":
            error(
                "Reviewed cards must use 'dos approve' so the named decision and its "
                "evidence are recorded.",
                as_json=context.as_json,
                code="approval_required",
            )
            return EXIT_USAGE
        try:
            moved = move_card(card, args.to_state, by=args.by, now=datetime.now(UTC))
        except IllegalTransition as exc:
            error(
                f"{card.id}: cannot move {exc}. Allowed next states: "
                f"{', '.join(next_states(card)) or 'none'}.",
                as_json=context.as_json,
                code="illegal_transition",
            )
            return EXIT_USAGE
        blocking = lint_card(moved) if args.to_state in {"contest", "commit"} else []
        blocking = [finding for finding in blocking if finding.rule != "legacy-schema"]
        if blocking:
            error(
                "Cannot request or record approval until these fields are fixed:\n"
                + "\n".join(f"- {finding.message}" for finding in blocking),
                as_json=context.as_json,
                code="incomplete_card",
            )
            return EXIT_USAGE
        if not args.dry_run:
            code = write_or_conflict(moved, as_json=context.as_json)
            if code:
                return code
        payload = {
            "id": moved.id,
            "from": card.state,
            "to": moved.state,
            "by": args.by,
            "dry_run": args.dry_run,
        }
        text = (
            f"{'Would move' if args.dry_run else 'Moved'} {moved.id}: {card.state} -> {moved.state}"
        )
        emit(payload if context.as_json else text, as_json=context.as_json)
        return EXIT_OK

    if args.cmd == "approve":
        card = find_card_or_error(context, args.card_id)
        if card is None:
            return EXIT_USAGE
        try:
            approved = record_approval(
                card,
                approved_by=args.approved_by,
                recorded_by=args.recorded_by,
                evidence=args.evidence,
                now=datetime.now(UTC),
            )
        except IllegalTransition as exc:
            error(f"{card.id}: {exc}", as_json=context.as_json, code="approval_rejected")
            return EXIT_USAGE
        blocking = [finding for finding in lint_card(approved) if finding.rule != "legacy-schema"]
        if blocking:
            error(
                "Cannot approve:\n" + "\n".join(f"- {finding.message}" for finding in blocking),
                as_json=context.as_json,
                code="incomplete_card",
            )
            return EXIT_USAGE
        if not args.dry_run:
            code = write_or_conflict(approved, as_json=context.as_json)
            if code:
                return code
        payload = {
            "id": card.id,
            "approved_by": args.approved_by,
            "evidence": args.evidence,
            "dry_run": args.dry_run,
        }
        text = f"{'Would approve' if args.dry_run else 'Approved'} {card.id} by {args.approved_by}"
        emit(payload if context.as_json else text, as_json=context.as_json)
        return EXIT_OK

    if args.cmd == "verify":
        return _handle_verify(args, context)

    if args.cmd == "observe":
        card = find_card_or_error(context, args.card_id)
        if card is None:
            return EXIT_USAGE
        if card.state != "observe":
            error(
                f"{card.id} is in {card.state}; move it to observe first.",
                as_json=context.as_json,
                code="wrong_state",
            )
            return EXIT_USAGE
        warning = None
        if card.observation_date and card.observation_date > date.today():
            warning = f"observation is {(card.observation_date - date.today()).days} days early"
        observed = record_observation(
            card,
            value_moved=args.value_moved,
            delta_held=args.delta_held,
            by=args.by,
            now=datetime.now(UTC),
        )
        if not args.dry_run:
            code = write_or_conflict(observed, as_json=context.as_json)
            if code:
                return code
        payload = {
            "id": card.id,
            "value_moved": args.value_moved,
            "delta_held": args.delta_held,
            "warning": warning,
            "dry_run": args.dry_run,
        }
        text = (
            f"{'Would observe' if args.dry_run else 'Observed'} {card.id}: business value "
            f"{'moved' if args.value_moved else 'did not move'}; behaviour "
            f"{'matched the claim' if args.delta_held else 'did not match the claim'}"
        )
        if warning:
            text += f"\nWarning: {warning}."
        emit(payload if context.as_json else text, as_json=context.as_json)
        return EXIT_OK

    if args.cmd == "migrate":
        return _handle_migrate(args, context)

    if args.cmd == "archive":
        return _handle_archive(args, context)

    return _handle_restore(args, context)


def _handle_verify(args: Any, context: CommandContext) -> int:
    card = find_card_or_error(context, args.card_id)
    if card is None:
        return EXIT_USAGE
    if card.state != "verify" and not args.no_record:
        error(
            f"{card.id} is in {card.state}; move it to verify before running "
            "its acceptance command.",
            as_json=context.as_json,
            code="wrong_state",
        )
        return EXIT_USAGE
    try:
        plan = plan_eval(
            card,
            context.config.project_root,
            default_timeout_seconds=context.config.default_eval_timeout_seconds,
            allowed_environment=context.config.allowed_eval_environment,
        )
    except ValueError as exc:
        error(f"{card.id}: {exc}", as_json=context.as_json, code="eval_configuration")
        return EXIT_EVAL_ERROR
    if args.dry_run:
        payload = {
            "id": card.id,
            "command": list(plan.command),
            "preflight": list(plan.preflight) if plan.preflight else None,
            "working_directory": plan.working_directory,
            "timeout_seconds": plan.timeout_seconds,
            "dry_run": True,
        }
        text = ""
        if plan.preflight:
            text += f"Would check: {shlex.join(plan.preflight)}\n"
        text += f"Would run: {shlex.join(plan.command)}"
        emit(payload if context.as_json else text, as_json=context.as_json)
        return EXIT_OK
    result: EvalResult = run_eval(plan)
    if result.outcome in {"error", "timeout"}:
        payload = {"id": card.id, **result.as_dict(), "recorded": False}
        if context.as_json:
            emit(payload, as_json=True)
        else:
            error(
                f"{card.id} verification {result.outcome.upper()}; nothing recorded.\n"
                f"{result.stderr.strip()}",
                as_json=False,
                code="eval_error",
            )
        return EXIT_EVAL_ERROR
    if args.no_record:
        payload = {"id": card.id, **result.as_dict(), "recorded": False}
        if context.as_json:
            emit(payload, as_json=True)
        else:
            emit(f"{card.id} verification {result.outcome}; history unchanged", as_json=False)
            if result.stdout.strip():
                print(result.stdout.rstrip())
            if result.stderr.strip():
                print(result.stderr.rstrip(), file=sys.stderr)
        return EXIT_OK if result.outcome == "pass" else EXIT_FINDINGS
    updated = record_verify(
        card,
        passed=result.outcome == "pass",
        by=args.by,
        now=datetime.now(UTC),
        command=list(result.command),
        exit_code=result.exit_code,
        duration_seconds=result.duration_seconds,
    )
    code = write_or_conflict(updated, as_json=context.as_json)
    if code:
        return code
    payload = {"id": card.id, **result.as_dict(), "recorded": True}
    if context.as_json:
        emit(payload, as_json=True)
    else:
        emit(f"{card.id} verification {result.outcome} ({result.duration_seconds}s)", as_json=False)
        if result.outcome == "fail" and result.stdout.strip():
            print(result.stdout.rstrip())
    return EXIT_OK if result.outcome == "pass" else EXIT_FINDINGS


def _handle_migrate(args: Any, context: CommandContext) -> int:
    selected = (
        context.cards
        if not args.card_id
        else [card for card in context.cards if card.id == args.card_id]
    )
    if args.card_id and not selected:
        error(
            f"No card with ID {args.card_id} exists under {context.root}.",
            as_json=context.as_json,
            code="card_not_found",
        )
        return EXIT_USAGE
    changed: list[str] = []
    for card in selected:
        migrated = migrate_card(card)
        if migrated.schema_version == card.schema_version and migrated.eval == card.eval:
            continue
        changed.append(card.id)
        if not args.dry_run:
            code = write_or_conflict(migrated, as_json=context.as_json)
            if code:
                return code
    payload = {
        "migrated": changed,
        "schema_version": CURRENT_SCHEMA_VERSION,
        "dry_run": args.dry_run,
    }
    text = ("Would migrate " if args.dry_run else "Migrated ") + (
        ", ".join(changed) if changed else "no cards; everything is current"
    )
    emit(payload if context.as_json else text, as_json=context.as_json)
    return EXIT_OK


def _handle_archive(args: Any, context: CommandContext) -> int:
    card = find_card_or_error(context, args.card_id)
    if card is None:
        return EXIT_USAGE
    if card.state != "closed":
        error(
            f"Only closed cards can be archived; {card.id} is {card.state}.",
            as_json=context.as_json,
            code="archive_not_closed",
        )
        return EXIT_USAGE
    children = sorted(item.id for item in context.cards if item.parent == card.id)
    if children:
        error(
            f"Cannot archive {card.id}; active cards reference it: {', '.join(children)}.",
            as_json=context.as_json,
            code="archive_referenced",
        )
        return EXIT_USAGE
    if not args.yes and not args.dry_run:
        error(
            "Archive requires --yes. Use --dry-run to inspect the destination.",
            as_json=context.as_json,
            code="confirmation_required",
        )
        return EXIT_USAGE
    assert card.path is not None
    try:
        relative = card.path.resolve().relative_to(context.root.resolve())
    except ValueError:
        error(
            f"{card.path} is not inside the configured cards directory.",
            as_json=context.as_json,
            code="archive_path",
        )
        return EXIT_USAGE
    destination = context.config.archive_path / relative
    if destination.exists():
        error(
            f"Archive destination already exists: {destination}",
            as_json=context.as_json,
            code="archive_exists",
        )
        return EXIT_USAGE
    if not args.dry_run:
        try:
            _move_without_overwrite(card.path, destination)
        except OSError as exc:
            error(
                f"Cannot archive {card.id}: {exc}",
                as_json=context.as_json,
                code="archive_failed",
            )
            return EXIT_CONFLICT
    payload = {
        "id": card.id,
        "from": card.path,
        "to": destination,
        "dry_run": args.dry_run,
        "recoverable": True,
    }
    text = f"{'Would archive' if args.dry_run else 'Archived'} {card.id} to {destination}"
    emit(payload if context.as_json else text, as_json=context.as_json)
    return EXIT_OK


def _handle_restore(args: Any, context: CommandContext) -> int:
    try:
        archived_cards = load_all(context.config.archive_path)
    except (ValueError, OSError) as exc:
        error(f"Cannot load archive: {exc}", as_json=context.as_json, code="archive_load_error")
        return EXIT_USAGE
    archived = find_card(archived_cards, args.card_id)
    if archived is None:
        error(
            f"No archived card with ID {args.card_id} exists.",
            as_json=context.as_json,
            code="archived_card_not_found",
        )
        return EXIT_USAGE
    active_with_same_id = find_card(context.cards, archived.id)
    if active_with_same_id is not None:
        error(
            f"Cannot restore {archived.id}; active card {active_with_same_id.path} "
            "already uses that ID.",
            as_json=context.as_json,
            code="restore_duplicate_id",
        )
        return EXIT_USAGE
    if archived.parent and find_card(context.cards, archived.parent) is None:
        error(
            f"Restore parent {archived.parent} before restoring {archived.id}.",
            as_json=context.as_json,
            code="restore_parent_missing",
        )
        return EXIT_USAGE
    if not args.yes and not args.dry_run:
        error(
            "Restore requires --yes. Use --dry-run to inspect the destination.",
            as_json=context.as_json,
            code="confirmation_required",
        )
        return EXIT_USAGE
    assert archived.path is not None
    relative = archived.path.resolve().relative_to(context.config.archive_path)
    destination = context.root / relative
    if destination.exists():
        error(
            f"Restore destination already exists: {destination}",
            as_json=context.as_json,
            code="restore_exists",
        )
        return EXIT_USAGE
    if not args.dry_run:
        try:
            _move_without_overwrite(archived.path, destination)
        except OSError as exc:
            error(
                f"Cannot restore {archived.id}: {exc}",
                as_json=context.as_json,
                code="restore_failed",
            )
            return EXIT_CONFLICT
    payload = {
        "id": archived.id,
        "from": archived.path,
        "to": destination,
        "dry_run": args.dry_run,
    }
    text = f"{'Would restore' if args.dry_run else 'Restored'} {archived.id} to {destination}"
    emit(payload if context.as_json else text, as_json=context.as_json)
    return EXIT_OK
