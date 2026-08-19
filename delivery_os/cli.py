from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from delivery_os.card import load_all, load_card, write_card
from delivery_os.gh import PR_EVENTS, card_ids_in_paths, load_deciders, transition_for
from delivery_os.lint import lint_card
from delivery_os.machine import IllegalTransition, move_card, record_verify
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
        f"M2 eval fallibility   {m2['headline']}"
        f"   proven {m2['proven_fallible']}/{m2['in_scope']}"
        f"   never-run {len(m2['never_run'])}   never-red {len(m2['never_red'])}"
        f"   no-eval {len(m2['without_eval'])}",
        f"M3 behaviour-delta debt  live {m3['live_deltas']}   unowned {len(m3['unowned'])}",
        "",
        f"SCOREBOARD  value lines moved {sb['headline']}   unrecorded {len(sb['unrecorded'])}",
    ]
    for item in m1["open"]:
        lines.append(f"  waiting {item['hours']}h on {item['decider']} for {item['id']}")
    for card_id in sb["unrecorded"]:
        lines.append(f"  observation overdue: {card_id}")
    return "\n".join(lines)


# pytest exit codes. Only 1 means the eval genuinely went red; everything
# else means the eval did not get to express an opinion.
#   0 all passed | 1 tests failed | 2 interrupted
#   3 internal error | 4 usage error | 5 no tests collected
_PYTEST_PASSED = 0
_PYTEST_FAILED = 1


def verify_card(card, repo_root=".") -> tuple[str, str, str]:
    """Run a card's acceptance eval. Returns (outcome, stdout, stderr).

    outcome is one of:
      "pass"  - the eval ran and was green (exit 0)
      "fail"  - the eval ran and went red (exit 1)
      "error" - the eval could not run at all (any other exit code, or no
                eval on the card). This is NOT a red result and must never
                reach card history: spec 5 presumes an eval that has never
                been red to be broken, so recording an unrunnable eval as
                `verify: fail` would satisfy that guard with pure theatre.

    `card.eval` is a pytest node id relative to the REPOSITORY root
    (e.g. "evals/C-0001_test.py::test_x"), not to --root. --root locates
    the card corpus; it is deliberately not threaded through here.
    """
    if not card.eval:
        return "error", "", "card has no eval: nothing to run"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", card.eval, "-q"],
        capture_output=True, text=True, cwd=repo_root,
    )
    if result.returncode == _PYTEST_PASSED:
        return "pass", result.stdout, result.stderr
    if result.returncode == _PYTEST_FAILED:
        return "fail", result.stdout, result.stderr
    return (
        "error",
        result.stdout,
        f"{result.stderr}\npytest exited {result.returncode}: the eval could not run",
    )


def _find(cards, card_id: str, root) -> object | None:
    """The card with this id, or None after printing a clean diagnosis.

    `next(c for c in cards if ...)` raised a bare StopIteration, which in
    card-sync fails the job with a traceback and no explanation.
    """
    for card in cards:
        if card.id == card_id:
            return card
    print(f"no card with id {card_id} under {root}", file=sys.stderr)
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="dos")
    parser.add_argument("--root", default="cards",
                        help="directory holding the card corpus (not used to resolve evals)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new")
    p_new.add_argument("engagement")
    p_new.add_argument("title")
    p_new.add_argument("--tier", default="T1", choices=["T1", "T2"])
    p_new.add_argument("--parent", default=None)

    sub.add_parser("lint")
    sub.add_parser("report")

    p_move = sub.add_parser("move")
    p_move.add_argument("card_id")
    p_move.add_argument("to_state")
    p_move.add_argument("--by", required=True)

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("card_id")

    p_sync = sub.add_parser("sync-pr")
    p_sync.add_argument("--changed", required=True, help="newline- or comma-separated paths")
    p_sync.add_argument("--approvers", default="", help="comma-separated GitHub handles")
    p_sync.add_argument("--pr-state", required=True, choices=PR_EVENTS,
                        help="what the PR did: opened/updated, merged, or closed unmerged")
    p_sync.add_argument("--deciders", default="contract/deciders.yml")

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
        card = _find(cards, args.card_id, args.root)
        if card is None:
            return 2
        try:
            moved = move_card(card, args.to_state, by=args.by,
                              now=datetime.now(timezone.utc))
        except IllegalTransition as exc:
            # A bare traceback here fails the card-sync job with no diagnosis.
            print(f"{card.id}: illegal transition {exc}", file=sys.stderr)
            return 2
        write_card(moved)
        print(f"{moved.id} -> {moved.state}")
        return 0

    if args.cmd == "verify":
        card = _find(cards, args.card_id, args.root)
        if card is None:
            return 2
        outcome, out, err = verify_card(card)
        if outcome == "error":
            # Not recorded: an eval that could not run has proved nothing.
            print(f"{card.id} verify ERROR: eval could not run - nothing recorded",
                  file=sys.stderr)
            if out.strip():
                print(out, file=sys.stderr)
            if err.strip():
                print(err.strip(), file=sys.stderr)
            return 3
        updated = record_verify(card, passed=outcome == "pass", by="cli",
                                now=datetime.now(timezone.utc))
        write_card(updated)
        print(f"{card.id} verify {outcome}")
        if outcome == "fail":
            print(out)
        return 0 if outcome == "pass" else 1

    if args.cmd == "sync-pr":
        changed = [p for p in re.split(r"[,\n]", args.changed) if p.strip()]
        approvers = [a.strip() for a in args.approvers.split(",") if a.strip()]
        deciders = load_deciders(args.deciders)
        wanted = card_ids_in_paths(changed)
        by_id = {c.id: c for c in cards}
        for card_id in wanted:
            card = by_id.get(card_id)
            if card is None:
                # Never silent: this silence is what concealed C3 for eleven
                # reviews. A changed path naming a card that is not in the
                # corpus means the corpus was read from the wrong ref, the
                # file is not a card, or the id and filename disagree.
                print(f"{card_id}  not found under {args.root} (no state written)")
                continue
            target = transition_for(card, args.pr_state, approvers, deciders)
            if target is None:
                print(f"{card_id}  no transition")
                continue
            moved = move_card(card, target, by="github", now=datetime.now(timezone.utc))
            write_card(moved)
            print(f"{card_id} -> {target}")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
