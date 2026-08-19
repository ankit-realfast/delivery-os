"""I1/I8: the loader validated field names but never types, and crashed on
any non-card .md in the corpus.

Both shapes below lint clean and take down `dos report` for the ENTIRE
corpus -- one bad card blinds the client-facing report.
"""
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from delivery_os.card import load_all, load_card
from delivery_os.cli import render_report
from delivery_os.meters import compute_m1, compute_scoreboard

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


# --- I1: history `at` timestamps -------------------------------------------

UNQUOTED_AT = """---
id: C-0001
title: t
tier: T1
state: commit
parent: C-0000
eval: evals/x.py::test_x
history:
  - {state: contest, at: 2026-08-01T09:00:00Z, by: akp}
  - {state: commit, at: 2026-08-02T09:00:00Z, by: priya}
---
Body.
"""


def test_unquoted_timestamp_is_coerced_not_left_as_a_datetime(tmp_path):
    # Unquoted YAML timestamps resolve to datetime objects, and
    # meters._last_entry_at then called datetime.fromisoformat(datetime).
    card = load_card(_write(tmp_path, "C-0001.md", UNQUOTED_AT))
    assert all(isinstance(h["at"], str) for h in card.history)
    assert compute_m1([card], now=NOW)["median_hours"] == 24.0


def test_a_card_with_unquoted_timestamps_does_not_blind_the_report(tmp_path):
    card = load_card(_write(tmp_path, "C-0001.md", UNQUOTED_AT))
    assert "M1 decision latency" in render_report([card], now=NOW, today=date(2026, 10, 1))


def test_naive_timestamp_is_rejected_at_load_not_at_report_time(tmp_path):
    body = UNQUOTED_AT.replace("at: 2026-08-01T09:00:00Z", 'at: "2026-08-01T09:00:00"')
    with pytest.raises(ValueError, match="timezone"):
        load_card(_write(tmp_path, "C-0001.md", body))


def test_unparseable_timestamp_is_rejected_at_load(tmp_path):
    body = UNQUOTED_AT.replace("at: 2026-08-01T09:00:00Z", 'at: "last tuesday"')
    with pytest.raises(ValueError, match="ISO timestamp"):
        load_card(_write(tmp_path, "C-0001.md", body))


def test_history_entry_without_a_timestamp_is_rejected(tmp_path):
    body = UNQUOTED_AT.replace("{state: contest, at: 2026-08-01T09:00:00Z, by: akp}",
                               "{state: contest, by: akp}")
    with pytest.raises(ValueError, match="no 'at' timestamp"):
        load_card(_write(tmp_path, "C-0001.md", body))


def test_history_that_is_not_a_list_is_rejected(tmp_path):
    body = UNQUOTED_AT[:UNQUOTED_AT.index("history:")] + "history: yesterday\n---\nBody.\n"
    with pytest.raises(ValueError, match="'history' must be a list"):
        load_card(_write(tmp_path, "C-0001.md", body))


# --- I1: observation_date ---------------------------------------------------

QUOTED_DATE = """---
id: C-0001
title: t
tier: T2
state: observe
parent: null
decider: Priya
eval: evals/x.py::test_x
value_line: "v"
kill_criterion: "k"
observation_date: "2026-09-30"
value_moved: true
---
Body.
"""


def test_quoted_observation_date_is_coerced_to_a_date(tmp_path):
    # A str <= date comparison raises TypeError inside compute_scoreboard.
    card = load_card(_write(tmp_path, "C-0001.md", QUOTED_DATE))
    assert card.observation_date == date(2026, 9, 30)
    assert compute_scoreboard([card], today=date(2026, 10, 1))["moved"] == ["C-0001"]


def test_a_card_with_a_quoted_date_does_not_blind_the_report(tmp_path):
    card = load_card(_write(tmp_path, "C-0001.md", QUOTED_DATE))
    assert "SCOREBOARD" in render_report([card], now=NOW, today=date(2026, 10, 1))


def test_a_nonsense_observation_date_is_rejected_at_load(tmp_path):
    body = QUOTED_DATE.replace('observation_date: "2026-09-30"',
                               'observation_date: "next quarter"')
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        load_card(_write(tmp_path, "C-0001.md", body))


# --- I1: booleans and required fields ---------------------------------------

def test_a_string_where_a_boolean_belongs_is_rejected(tmp_path):
    body = """---
id: C-0001
title: t
tier: T1
state: draft
parent: C-0000
touches_auth: "yes"
---
Body.
"""
    with pytest.raises(ValueError, match="touches_auth"):
        load_card(_write(tmp_path, "C-0001.md", body))


def test_a_list_where_text_belongs_is_rejected(tmp_path):
    body = "---\nid: C-0001\ntitle: t\ntier: T1\nstate: draft\neval: [a, b]\n---\nBody.\n"
    with pytest.raises(ValueError, match="'eval' must be text"):
        load_card(_write(tmp_path, "C-0001.md", body))


def test_a_card_with_no_id_is_a_clean_error_not_a_typeerror(tmp_path):
    body = "---\ntitle: t\ntier: T1\nstate: draft\n---\nBody.\n"
    with pytest.raises(ValueError, match="missing required field"):
        load_card(_write(tmp_path, "C-0001.md", body))


def test_explicit_nulls_fall_back_to_the_dataclass_default(tmp_path):
    # Templates ship `eval: null` / `blocked_on: null` as placeholders.
    body = ("---\nid: C-0001\ntitle: t\ntier: T1\nstate: draft\nparent: C-0000\n"
            "eval: null\nblocked_on: null\nbehaviour_delta: null\n---\nBody.\n")
    card = load_card(_write(tmp_path, "C-0001.md", body))
    assert card.eval is None
    assert card.behaviour_delta == "none"


# --- I8: non-card files in the corpus ---------------------------------------

def test_a_readme_in_the_corpus_is_skipped_not_a_traceback(tmp_path):
    (tmp_path / "README.md").write_text("# Cards\n\nHow this corpus works.\n", encoding="utf-8")
    _write(tmp_path, "C-0001.md", QUOTED_DATE)
    assert [c.id for c in load_all(tmp_path)] == ["C-0001"]


def test_dos_lint_exits_cleanly_with_a_readme_in_the_corpus(tmp_path, monkeypatch):
    from delivery_os.cli import main
    cards = tmp_path / "cards"
    cards.mkdir()
    (cards / "README.md").write_text("# Cards\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["--root", "cards", "lint"]) == 0


def test_a_malformed_card_still_raises(tmp_path):
    # A file WITH frontmatter that is broken is a broken card, not a non-card.
    (tmp_path / "C-0001.md").write_text(
        "---\nid: C-0001\ntitle: t\ntier: T1\nstate: draft\ntouches_auth: nope\n---\nB\n",
        encoding="utf-8")
    with pytest.raises(ValueError, match="touches_auth"):
        load_all(tmp_path)
