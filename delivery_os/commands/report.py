from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from delivery_os.card import Card
from delivery_os.commands.common import EXIT_OK, EXIT_USAGE, CommandContext, emit, error
from delivery_os.meters import (
    METRIC_VERSION,
    compute_m1,
    compute_m2,
    compute_m3,
    compute_scoreboard,
)

COMMANDS = frozenset({"report"})


def register(subparsers: Any) -> None:
    report = subparsers.add_parser("report", help="show decision and outcome measures")
    report.add_argument("--at", help="ISO timestamp used for deterministic decision latency")
    report.add_argument("--today", help="YYYY-MM-DD used to decide which observations are due")
    report.add_argument("--explain", action="store_true", help="explain each measure")


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--at requires a timezone offset, for example 2026-08-21T12:00:00+00:00")
    return parsed


def _parse_date(value: str | None, fallback: date) -> date:
    return date.fromisoformat(value) if value else fallback


def report_data(cards: list[Card], *, now: datetime, today: date) -> dict[str, Any]:
    return {
        "metric_version": METRIC_VERSION,
        "as_of": now,
        "decision_latency": compute_m1(cards, now=now),
        "acceptance_test_evidence": compute_m2(cards),
        "behaviour_change_debt": compute_m3(cards),
        "business_results": compute_scoreboard(cards, today=today),
    }


def render_report(cards: list[Card], now: datetime, today: date) -> str:
    data = report_data(cards, now=now, today=today)
    decision = data["decision_latency"]
    evidence = data["acceptance_test_evidence"]
    behaviour = data["behaviour_change_debt"]
    results = data["business_results"]
    median = "n/a" if decision["median_hours"] is None else f"{decision['median_hours']}h"
    evidence_head = "n/a" if evidence["headline"] is None else evidence["headline"]
    results_head = "n/a" if results["headline"] is None else results["headline"]
    lines = []
    if not cards:
        lines += ["No cards yet. Create one with 'dos new <engagement> <title>'.", ""]
    lines += [
        f"Decision latency (M1)      median {median}   waiting {len(decision['open'])}",
        f"Acceptance evidence (M2)  {evidence_head}   proven {evidence['proven_fallible']}/"
        f"{evidence['in_scope']}   never run {len(evidence['never_run'])}   "
        f"never failed {len(evidence['never_red'])}",
        f"Behaviour changes (M3)    live {behaviour['live_deltas']}   "
        f"without owner {len(behaviour['unowned'])}   "
        f"claim disproved {len(behaviour['disproved'])}",
        "",
        f"Business results           moved {results_head}   due {len(results['due'])}   "
        f"not recorded {len(results['unrecorded'])}",
    ]
    for item in decision["open"]:
        lines.append(f"  Waiting {item['hours']}h on {item['decider']} for {item['id']}")
    for card_id in results["unrecorded"]:
        lines.append(f"  Observation overdue: {card_id}")
    return "\n".join(lines)


def _explanations() -> dict[str, Any]:
    return {
        "metric_version": METRIC_VERSION,
        "decision_latency": "Hours from requesting reviewed approval to receiving it.",
        "acceptance_test_evidence": (
            "Share of accepted cards whose acceptance command has demonstrably "
            "failed at least once."
        ),
        "behaviour_change_debt": (
            "Unfinished cards that change externally visible behaviour, including owner gaps."
        ),
        "business_results": "Share of due, recorded business targets that actually improved.",
    }


def handle(args: Any, context: CommandContext) -> int:
    if args.explain:
        data = _explanations()
        if context.as_json:
            emit(data, as_json=True)
        else:
            emit(
                "\n".join(
                    f"{name.replace('_', ' ').title()}: {meaning}"
                    for name, meaning in data.items()
                    if name != "metric_version"
                ),
                as_json=False,
            )
        return EXIT_OK
    try:
        now = _parse_datetime(args.at)
        today = _parse_date(args.today, now.date())
    except ValueError as exc:
        error(str(exc), as_json=context.as_json, code="bad_date")
        return EXIT_USAGE
    output = (
        report_data(context.cards, now=now, today=today)
        if context.as_json
        else render_report(context.cards, now, today)
    )
    emit(output, as_json=context.as_json)
    return EXIT_OK
