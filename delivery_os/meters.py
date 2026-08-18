from __future__ import annotations

from datetime import datetime
from statistics import median

from delivery_os.card import Card, state_index


def _last_entry_at(card: Card, state: str) -> datetime | None:
    stamps = [h["at"] for h in card.history if h.get("state") == state and "verify" not in h]
    return datetime.fromisoformat(stamps[-1]) if stamps else None


def _hours(start: datetime, end: datetime) -> float:
    return round((end - start).total_seconds() / 3600, 2)


def compute_m1(cards: list[Card], now: datetime) -> dict:
    closed_durations: list[float] = []
    by_decider: dict[str, list[float]] = {}
    open_items: list[dict] = []

    for card in cards:
        entered = _last_entry_at(card, "contest")
        if entered is None:
            continue
        committed = _last_entry_at(card, "commit")
        if committed is not None and committed > entered:
            hours = _hours(entered, committed)
            closed_durations.append(hours)
            by_decider.setdefault(card.decider or "unassigned", []).append(hours)
        elif card.state == "contest":
            open_items.append(
                {"id": card.id, "decider": card.decider, "hours": _hours(entered, now)}
            )

    return {
        "headline": median(closed_durations) if closed_durations else None,
        "median_hours": median(closed_durations) if closed_durations else None,
        "by_decider": {k: median(v) for k, v in by_decider.items()},
        "open": sorted(open_items, key=lambda o: -o["hours"]),
    }


def compute_m2(cards: list[Card]) -> dict:
    scope = [c for c in cards if state_index(c.state) >= state_index("commit")]
    with_eval = [c for c in scope if c.eval]
    without_eval = [c.id for c in scope if not c.eval]
    never_red = [
        c.id for c in with_eval
        if not any(h.get("verify") == "fail" for h in c.history)
        and any(h.get("verify") for h in c.history)
    ]
    headline = round(len(with_eval) / len(scope), 2) if scope else None
    return {
        "headline": headline,
        "in_scope": len(scope),
        "with_eval": len(with_eval),
        "without_eval": sorted(without_eval),
        "never_red": sorted(never_red),
    }


def compute_m3(cards: list[Card]) -> dict:
    live = [c for c in cards if c.state != "closed" and c.behaviour_delta != "none"]
    unowned = [c.id for c in live if not c.delta_owner]
    return {
        "headline": len(live),
        "live_deltas": len(live),
        "unowned": sorted(unowned),
    }
