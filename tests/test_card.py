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


def test_title_with_unquoted_triple_dash_is_preserved(tmp_path):
    # Regression: naive substring split would truncate at the first ---
    body = """---
id: C-0099
title: fix pipeline step - a --- b step
tier: T1
state: draft
---
Body text here.
"""
    card = load_card(_write(tmp_path, "C-0099.md", body))
    assert card.id == "C-0099"
    assert card.title == "fix pipeline step - a --- b step"
    assert card.tier == "T1"
    assert card.state == "draft"


def test_value_line_with_quoted_triple_dash_is_preserved(tmp_path):
    # Regression: naive substring split would fail on quoted --- in YAML
    body = """---
id: C-0098
title: webhook delivery
tier: T2
state: commit
value_line: "before --- after"
---
Body text here.
"""
    card = load_card(_write(tmp_path, "C-0098.md", body))
    assert card.id == "C-0098"
    assert card.value_line == "before --- after"


def test_unterminated_frontmatter_is_rejected(tmp_path):
    # Only opening ---, no closing --- delimiter
    body = """---
id: C-0097
title: incomplete
tier: T1
state: draft
"""
    with pytest.raises(ValueError, match="frontmatter"):
        load_card(_write(tmp_path, "C-0097.md", body))


def test_body_with_markdown_horizontal_rule_is_preserved(tmp_path):
    # Markdown horizontal rule (--- on its own line) should stay in body
    body = """---
id: C-0096
title: with horizontal rule
tier: T1
state: draft
---
This is the body.

---

That was a horizontal rule.
"""
    card = load_card(_write(tmp_path, "C-0096.md", body))
    assert card.id == "C-0096"
    assert "---" in card.intent
    assert card.intent == "This is the body.\n\n---\n\nThat was a horizontal rule."


def test_load_all_raises_on_a_card_with_a_typod_closing_fence(tmp_path):
    # I8 made load_all skip files _split_frontmatter can't parse, so a
    # README no longer crashes `dos lint`. But a card whose closing fence
    # is typo'd ('--' instead of '---') opens a real frontmatter block and
    # never closes it -- that is a broken card, not a non-card, and must
    # raise rather than silently vanish from the corpus.
    body = """---
id: C-0094
title: broken closing fence
tier: T1
state: draft
--
Body text that never actually left the frontmatter.
"""
    _write(tmp_path, "C-0094.md", body)
    with pytest.raises(ValueError, match="frontmatter"):
        load_all(tmp_path)


def test_load_all_loads_a_card_with_a_leading_utf8_bom(tmp_path):
    # A UTF-8 BOM before the opening fence must not disguise a real card as
    # one with no frontmatter at all.
    raw = "﻿" + T1_CARD
    p = tmp_path / "C-0002-retry.md"
    p.write_bytes(raw.encode("utf-8"))
    cards = load_all(tmp_path)
    assert [c.id for c in cards] == ["C-0002"]


def test_load_all_still_skips_a_genuine_non_card_markdown_file(tmp_path):
    # A file with no opening fence at all -- a README, notes, a template --
    # is not a broken card and must stay skipped, not raise.
    _write(tmp_path, "README.md", "# Cards\n\nThis directory holds cards.\n")
    _write(tmp_path, "C-0002-retry.md", T1_CARD)
    cards = load_all(tmp_path)
    assert [c.id for c in cards] == ["C-0002"]


def test_intent_key_in_frontmatter_is_rejected(tmp_path):
    # intent is loader-owned; should not be in frontmatter
    body = """---
id: C-0095
title: bad key
tier: T1
state: draft
intent: should not be here
---
Actual body.
"""
    with pytest.raises(ValueError, match="unknown fields"):
        load_card(_write(tmp_path, "C-0095.md", body))
