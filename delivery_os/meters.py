from __future__ import annotations

from datetime import date, datetime
from statistics import median

from delivery_os.card import Card, state_at_least
from delivery_os.lint import effective_tier
from delivery_os.machine import ANNOTATION_KEYS


def _last_entry_at(card: Card, state: str) -> datetime | None:
    stamps = [h["at"] for h in card.history
              if h.get("state") == state
              and not any(k in h for k in ANNOTATION_KEYS)]
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
    """M2 -- eval fallibility (spec 5).

    The spec defines M2 as "share of committed cards with an eval *that can
    fail*", and operationalises "can fail" in the same section's guard table:
    "an eval that has never been red is presumed broken until it goes red
    once". Presence of a non-empty `eval:` string is therefore not the
    measure -- it is exactly the thing the guard exists to disbelieve.

    The headline is the share of in-scope cards whose eval has demonstrably
    gone red at least once. The two presumed-broken populations are reported
    separately because they need different actions:

      never_run  - has an eval, no verify has ever been recorded. Run it.
      never_red  - has run, has never failed. Prove it can fail.
    """
    scope = [c for c in cards if state_at_least(c.state, "commit")]
    with_eval = [c for c in scope if c.eval]
    without_eval = sorted(c.id for c in scope if not c.eval)

    def _ran(card: Card) -> bool:
        return any(h.get("verify") for h in card.history)

    def _went_red(card: Card) -> bool:
        return any(h.get("verify") == "fail" for h in card.history)

    proven_fallible = [c for c in with_eval if _went_red(c)]
    never_run = sorted(c.id for c in with_eval if not _ran(c))
    never_red = sorted(c.id for c in with_eval if _ran(c) and not _went_red(c))
    headline = round(len(proven_fallible) / len(scope), 2) if scope else None
    return {
        "headline": headline,
        "in_scope": len(scope),
        "with_eval": len(with_eval),
        "proven_fallible": len(proven_fallible),
        "without_eval": without_eval,
        "never_run": never_run,
        "never_red": never_red,
        "presumed_broken": sorted(set(never_run) | set(never_red)),
    }


def compute_m3(cards: list[Card]) -> dict:
    live = [c for c in cards if c.state != "closed" and c.behaviour_delta != "none"]
    unowned = [c.id for c in live if not c.delta_owner]
    # Spec 5's M3 guard: M3 is gamed by declaring "none" falsely, and "the
    # observation date checks the claim against reality". A card whose
    # observed delta did not hold is that check firing.
    disproved = sorted(c.id for c in cards if c.delta_held is False)
    return {
        "headline": len(live),
        "live_deltas": len(live),
        "unowned": sorted(unowned),
        "disproved": disproved,
    }


def compute_scoreboard(cards: list[Card], today: date) -> dict:
    due = [
        c for c in cards
        if effective_tier(c) == "T2" and c.observation_date and c.observation_date <= today
    ]
    recorded = [c for c in due if c.value_moved is not None]
    moved = [c.id for c in recorded if c.value_moved]
    not_moved = [c.id for c in recorded if not c.value_moved]
    headline = round(len(moved) / len(recorded), 2) if recorded else None
    return {
        "headline": headline,
        "due": sorted(c.id for c in due),
        "unrecorded": sorted(c.id for c in due if c.value_moved is None),
        "moved": sorted(moved),
        "not_moved": sorted(not_moved),
    }
