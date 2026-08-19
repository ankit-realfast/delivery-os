from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from delivery_os.card import load_all, load_card
from delivery_os.lint import lint_card
from delivery_os.machine import move_card, record_verify
from delivery_os.meters import compute_m1, compute_m2, compute_m3, compute_scoreboard

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def next_card_id(root: str | Path) -> str:
    ids = [int(m.group(1)) for p in Path(root).rglob("C-*.md")
           if (m := re.match(r"C-(\d{4})", p.name))]
    return f"C-{max(ids, default=0) + 1:04d}"


def new_card(root, engagement: str, title: str, tier: str, parent: str | None) -> Path:
    if parent is None:
        tier = "T2"          # a card with no parent is T2 by definition
    card_id = next_card_id(root)
    template = (TEMPLATES / f"card-{tier.lower()}.md").read_text(encoding="utf-8")
    # Templates quote {id} and {title}: a scalar opening with '{' would
    # otherwise parse as a YAML flow mapping. The title sits inside a
    # double-quoted YAML scalar, so both '\' and '"' must be escaped —
    # backslash first, or the quote-escape's own backslashes get doubled.
    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    body = template.format(id=card_id, title=safe_title, parent=parent or "null")
    out_dir = Path(root) / engagement
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{card_id}-{_slug(title)}.md"
    path.write_text(body, encoding="utf-8")
    return path


def render_report(cards, now: datetime, today: date) -> str:
    m1 = compute_m1(cards, now=now)
    m2 = compute_m2(cards)
    m3 = compute_m3(cards)
    sb = compute_scoreboard(cards, today=today)
    lines = [
        f"M1 decision latency   median {m1['median_hours']}h   open {len(m1['open'])}",
        f"M2 eval coverage      {m2['headline']}   never-red {len(m2['never_red'])}",
        f"M3 behaviour-delta debt  live {m3['live_deltas']}   unowned {len(m3['unowned'])}",
        "",
        f"SCOREBOARD  value lines moved {sb['headline']}   unrecorded {len(sb['unrecorded'])}",
    ]
    for item in m1["open"]:
        lines.append(f"  waiting {item['hours']}h on {item['decider']} for {item['id']}")
    for card_id in sb["unrecorded"]:
        lines.append(f"  observation overdue: {card_id}")
    return "\n".join(lines)


def verify_card(card, repo_root=".") -> tuple[bool, str]:
    """Run a card's acceptance eval. Returns (passed, output).

    `card.eval` is a pytest node id relative to the REPOSITORY root
    (e.g. "evals/C-0001_test.py::test_x"), not to --root. --root locates
    the card corpus; it is deliberately not threaded through here.
    """
    if not card.eval:
        return False, "card has no eval"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", card.eval, "-q"],
        capture_output=True, text=True, cwd=repo_root,
    )
    return result.returncode == 0, result.stdout


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="dos")
    parser.add_argument("--root", default="cards",
                        help="directory holding the card corpus (not used to resolve evals)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new")
    p_new.add_argument("engagement")
    p_new.add_argument("title")
    p_new.add_argument("--tier", default="T1")
    p_new.add_argument("--parent", default=None)

    sub.add_parser("lint")
    sub.add_parser("report")

    p_move = sub.add_parser("move")
    p_move.add_argument("card_id")
    p_move.add_argument("to_state")
    p_move.add_argument("--by", required=True)

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("card_id")

    args = parser.parse_args(argv)

    if args.cmd == "new":
        print(new_card(args.root, args.engagement, args.title, args.tier, args.parent))
        return 0

    cards = load_all(args.root)

    if args.cmd == "lint":
        findings = [f for c in cards for f in lint_card(c)]
        for f in findings:
            print(f"{f.card_id}  {f.rule}: {f.message}")
        return 1 if findings else 0

    if args.cmd == "report":
        print(render_report(cards, now=datetime.now(timezone.utc), today=date.today()))
        return 0

    if args.cmd == "move":
        card = next(c for c in cards if c.id == args.card_id)
        moved = move_card(card, args.to_state, by=args.by, now=datetime.now(timezone.utc))
        _rewrite(moved)
        print(f"{moved.id} -> {moved.state}")
        return 0

    if args.cmd == "verify":
        card = next(c for c in cards if c.id == args.card_id)
        passed, output = verify_card(card)
        updated = record_verify(card, passed=passed, by="cli", now=datetime.now(timezone.utc))
        _rewrite(updated)
        print(f"{card.id} verify {'pass' if passed else 'fail'}")
        if not passed:
            print(output)
        return 0 if passed else 1

    return 2


def _rewrite(card) -> None:
    import dataclasses

    import yaml

    data = {k: v for k, v in dataclasses.asdict(card).items()
            if k not in ("path", "intent")}
    front = yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
    card.path.write_text(f"---\n{front}---\n{card.intent}\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
