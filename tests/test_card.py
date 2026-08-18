from datetime import date
from pathlib import Path

import pytest

from delivery_os.card import Card, STATES, load_card, load_all, state_index

T1_CARD = """---
id: C-0002
title: retry failed webhook deliveries
tier: T1
state: draft
parent: C-0001
eval: evals/C-0002_test.py::test_retries_three_times
blocked_on: null
---
Failed webhook deliveries are retried three times with backoff.
"""

T2_CARD = """---
id: C-0001
title: webhook delivery subsystem
tier: T2
state: commit
parent: null
decider: Priya Raman <priya@client.example>
eval: evals/C-0001_test.py::test_delivery_succeeds
behaviour_delta: none
value_line: "support tickets for missed events: 40/mo -> 5/mo"
kill_criterion: "fewer than 20 missed events per month at baseline"
observation_date: 2026-09-30
touches_production_data: true
flag_off: false
history:
  - {state: draft, at: "2026-08-01T09:00:00Z", by: akp}
  - {state: contest, at: "2026-08-01T11:00:00Z", by: akp}
  - {state: commit, at: "2026-08-03T15:00:00Z", by: priya}
---
Events emitted by the platform reach the client's endpoint reliably.
"""


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_states_are_the_six_loop_states_plus_closed():
    assert STATES == ["draft", "contest", "commit", "build", "verify", "observe", "closed"]
    assert state_index("commit") > state_index("contest")


def test_load_t1_card_defaults_are_the_fast_lane(tmp_path):
    card = load_card(_write(tmp_path, "C-0002-retry.md", T1_CARD))
    assert card.id == "C-0002"
    assert card.tier == "T1"
    assert card.parent == "C-0001"
    assert card.behaviour_delta == "none"
    assert card.flag_off is True
    assert card.touches_production_data is False
    assert card.blocked_on is None
    assert card.intent.startswith("Failed webhook deliveries")


def test_load_t2_card_parses_typed_fields(tmp_path):
    card = load_card(_write(tmp_path, "C-0001-webhooks.md", T2_CARD))
    assert card.decider == "Priya Raman <priya@client.example>"
    assert card.observation_date == date(2026, 9, 30)
    assert card.flag_off is False
    assert len(card.history) == 3
    assert card.history[-1]["state"] == "commit"


def test_missing_frontmatter_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="frontmatter"):
        load_card(_write(tmp_path, "bad.md", "no frontmatter here\n"))


def test_unknown_field_is_rejected(tmp_path):
    body = "---\nid: C-0003\ntitle: t\ntier: T1\nstate: draft\nstory_points: 5\n---\nx\n"
    with pytest.raises(ValueError, match="story_points"):
        load_card(_write(tmp_path, "C-0003.md", body))


def test_load_all_finds_cards_recursively_and_sorts_by_id(tmp_path):
    (tmp_path / "acme").mkdir()
    _write(tmp_path / "acme", "C-0002-retry.md", T1_CARD)
    _write(tmp_path, "C-0001-webhooks.md", T2_CARD)
    cards = load_all(tmp_path)
    assert [c.id for c in cards] == ["C-0001", "C-0002"]
