from __future__ import annotations

import argparse
import sys
from pathlib import Path

from delivery_os.commands import cards, github, lifecycle, project, report
from delivery_os.commands.cards import new_card, next_card_id
from delivery_os.commands.common import (
    EXIT_USAGE,
    CommandContext,
    error,
    load_cards,
)
from delivery_os.commands.lifecycle import verify_card
from delivery_os.commands.report import render_report, report_data
from delivery_os.config import CONFIG_FILENAME, load_config
from delivery_os.version import __version__

__all__ = [
    "main",
    "new_card",
    "next_card_id",
    "render_report",
    "report_data",
    "verify_card",
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dos",
        description="Track decisions, acceptance evidence, and business outcomes as cards.",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="project directory; defaults to discovery from the current directory",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="card directory override; defaults to cards_root in project config",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--version", action="version", version=f"delivery-os {__version__}")
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    project.register(subparsers)
    cards.register(subparsers)
    lifecycle.register(subparsers)
    report.register(subparsers)
    github.register(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    json_anywhere = "--json" in raw_argv
    if json_anywhere:
        raw_argv = [argument for argument in raw_argv if argument != "--json"]
    args = parser.parse_args(raw_argv)
    as_json = args.json or json_anywhere

    if args.cmd == "init":
        return project.handle_init(args, as_json=as_json)

    try:
        config = load_config(args.project or ".")
    except (ValueError, OSError) as exc:
        error(f"Cannot load {CONFIG_FILENAME}: {exc}", as_json=as_json, code="config_error")
        return EXIT_USAGE
    root = Path(args.root).resolve() if args.root else config.cards_path

    if args.cmd == "version":
        return project.handle_version(config, as_json=as_json)

    loaded, load_code = load_cards(root, as_json=as_json)
    if loaded is None:
        return load_code
    context = CommandContext(config=config, root=root, cards=loaded, as_json=as_json)

    if args.cmd == "doctor":
        return project.handle_doctor(context)
    if args.cmd in cards.COMMANDS:
        return cards.handle(args, context)
    if args.cmd in lifecycle.COMMANDS:
        return lifecycle.handle(args, context)
    if args.cmd in report.COMMANDS:
        return report.handle(args, context)
    if args.cmd in github.COMMANDS:
        return github.handle(args, context)
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
