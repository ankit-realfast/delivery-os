from __future__ import annotations

import shlex
import sys
from importlib import resources
from pathlib import Path
from typing import Any

from delivery_os.card import CURRENT_SCHEMA_VERSION, load_all
from delivery_os.commands.common import (
    EXIT_FINDINGS,
    EXIT_OK,
    EXIT_USAGE,
    CommandContext,
    atomic_create,
    atomic_replace,
    emit,
    error,
)
from delivery_os.config import CONFIG_FILENAME, ProjectConfig, write_default_config
from delivery_os.eval_runner import command_available, plan_eval
from delivery_os.gh import load_deciders
from delivery_os.lint import lint_card, lint_corpus
from delivery_os.meters import METRIC_VERSION
from delivery_os.version import __version__

COMMANDS = frozenset({"doctor"})


def register(subparsers: Any) -> None:
    init = subparsers.add_parser("init", help="initialize delivery-os in a repository")
    init.add_argument("path", nargs="?", default=".")
    init.add_argument("--github", action="store_true", help="install GitHub workflows")
    init.add_argument("--force", action="store_true")
    init.add_argument("--dry-run", action="store_true")
    subparsers.add_parser("doctor", help="diagnose project configuration and dependencies")
    subparsers.add_parser("version", help="show delivery-os and schema versions")


def _install_github_workflows(root: Path, *, force: bool) -> list[Path]:
    source = resources.files("delivery_os") / "github"
    written: list[Path] = []
    for name in ("cards.yml", "card-sync.yml"):
        target = root / ".github" / "workflows" / name
        if target.exists() and not force:
            raise FileExistsError(f"{target} already exists; use --force to replace it")
        written.append(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (
            (source / name)
            .read_text(encoding="utf-8")
            .replace("__DELIVERY_OS_VERSION__", __version__)
        )
        if target.exists():
            atomic_replace(target, text)
        else:
            atomic_create(target, text)
    return written


def handle_init(args: Any, *, as_json: bool) -> int:
    init_root = Path(args.path).resolve()
    planned = [
        init_root / CONFIG_FILENAME,
        init_root / "cards" / "README.md",
        init_root / "archive" / "README.md",
        init_root / "contract" / "deciders.yml",
    ]
    if args.github:
        planned += [
            init_root / ".github" / "workflows" / "cards.yml",
            init_root / ".github" / "workflows" / "card-sync.yml",
        ]
    if args.dry_run:
        emit(
            {"dry_run": True, "would_create": [str(path) for path in planned]}
            if as_json
            else "Would create:\n" + "\n".join(f"  {path}" for path in planned),
            as_json=as_json,
        )
        return EXIT_OK
    try:
        config_path = write_default_config(init_root, force=args.force)
        (init_root / "cards").mkdir(parents=True, exist_ok=True)
        cards_readme = init_root / "cards" / "README.md"
        if not cards_readme.exists():
            atomic_create(
                cards_readme,
                "# Cards\n\nActive delivery-os cards live here, grouped by project.\n",
            )
        archive_readme = init_root / "archive" / "README.md"
        if not archive_readme.exists():
            atomic_create(
                archive_readme,
                "# Card archive\n\nClosed cards archived by delivery-os live in "
                "`archive/cards/`.\n",
            )
        deciders_file = init_root / "contract" / "deciders.yml"
        deciders_file.parent.mkdir(parents=True, exist_ok=True)
        if not deciders_file.exists():
            atomic_create(
                deciders_file,
                "# GitHub username -> exact decider value used on cards.\n{}\n",
            )
        workflows = _install_github_workflows(init_root, force=args.force) if args.github else []
    except (FileExistsError, OSError, ValueError) as exc:
        error(str(exc), as_json=as_json, code="init_failed")
        return EXIT_USAGE
    payload = {
        "initialized": str(init_root),
        "config": str(config_path),
        "workflows": [str(path) for path in workflows],
    }
    emit(payload if as_json else f"Initialized delivery-os in {init_root}", as_json=as_json)
    return EXIT_OK


def handle_version(config: ProjectConfig, *, as_json: bool) -> int:
    payload = {
        "delivery_os": __version__,
        "card_schema": CURRENT_SCHEMA_VERSION,
        "metric_schema": METRIC_VERSION,
        "config_schema": config.schema_version,
    }
    text = (
        f"delivery-os {__version__}\ncard schema {CURRENT_SCHEMA_VERSION}\n"
        f"metric schema {METRIC_VERSION}\nconfig schema {config.schema_version}"
    )
    emit(payload if as_json else text, as_json=as_json)
    return EXIT_OK


def handle_doctor(context: CommandContext) -> int:
    checks: list[dict[str, str]] = [
        {
            "name": "python",
            "status": "ok" if sys.version_info >= (3, 11) else "error",
            "detail": ".".join(str(part) for part in sys.version_info[:3]),
        },
        {
            "name": "configuration",
            "status": (
                "ok" if (context.config.project_root / CONFIG_FILENAME).exists() else "warning"
            ),
            "detail": str(context.config.project_root / CONFIG_FILENAME),
        },
        {
            "name": "cards directory",
            "status": "ok" if context.root.is_dir() else "warning",
            "detail": str(context.root),
        },
    ]
    try:
        decider_map = load_deciders(context.config.deciders_path)
        checks.append(
            {
                "name": "GitHub deciders",
                "status": "ok" if decider_map else "warning",
                "detail": (
                    f"{len(decider_map)} mapped GitHub identities"
                    if decider_map
                    else "no identities mapped; GitHub approval will fail closed"
                ),
            }
        )
    except (ValueError, OSError) as exc:
        checks.append({"name": "GitHub deciders", "status": "error", "detail": str(exc)})
    findings = [finding for card in context.cards for finding in lint_card(card)]
    findings += lint_corpus(context.cards, context.config.project_root)
    checks.append(
        {
            "name": "card collection",
            "status": "ok" if not findings else "error",
            "detail": f"{len(context.cards)} cards, {len(findings)} findings",
        }
    )
    try:
        archived_cards = load_all(context.config.archive_path)
        active_ids = {card.id for card in context.cards}
        archive_ids = [card.id for card in archived_cards]
        collisions = sorted(active_ids.intersection(archive_ids))
        duplicate_archive_ids = sorted(
            {card_id for card_id in archive_ids if archive_ids.count(card_id) > 1}
        )
        archive_errors = collisions or duplicate_archive_ids
        checks.append(
            {
                "name": "card archive",
                "status": "error" if archive_errors else "ok",
                "detail": (
                    "IDs active and archived: " + ", ".join(collisions)
                    if collisions
                    else "Duplicate archived IDs: " + ", ".join(duplicate_archive_ids)
                    if duplicate_archive_ids
                    else f"{len(archived_cards)} archived cards"
                ),
            }
        )
    except (ValueError, OSError) as exc:
        checks.append({"name": "card archive", "status": "error", "detail": str(exc)})
    for card in context.cards:
        if not card.eval:
            continue
        try:
            plan = plan_eval(
                card,
                context.config.project_root,
                default_timeout_seconds=context.config.default_eval_timeout_seconds,
                allowed_environment=context.config.allowed_eval_environment,
            )
            checks.append(
                {
                    "name": f"eval {card.id}",
                    "status": "ok" if command_available(plan) else "error",
                    "detail": shlex.join(plan.command),
                }
            )
        except ValueError as exc:
            checks.append({"name": f"eval {card.id}", "status": "error", "detail": str(exc)})
    artifacts = [
        name
        for name in (".venv", "delivery_os.egg-info")
        if (context.config.project_root / name).exists()
    ]
    if artifacts:
        checks.append(
            {
                "name": "source artifacts",
                "status": "warning",
                "detail": "unexpected checkout paths: " + ", ".join(artifacts),
            }
        )
    failed = any(check["status"] == "error" for check in checks)
    if context.as_json:
        emit({"checks": checks, "healthy": not failed}, as_json=True)
    else:
        icons = {"ok": "OK", "warning": "WARN", "error": "ERROR"}
        emit(
            "\n".join(
                f"{icons[check['status']]:5} {check['name']}: {check['detail']}" for check in checks
            ),
            as_json=False,
        )
    return EXIT_FINDINGS if failed else EXIT_OK
