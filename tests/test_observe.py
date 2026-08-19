"""I7: value_moved was read by the scoreboard and written by nothing.

The scoreboard is the OS's output number and the renewal argument, and
spec 4 calls Observe "the rule the system will most try to skip, and the
one that decides whether value can be proved at renewal."
"""
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from delivery_os.card import Card, load_card
from delivery_os.cli import main
from delivery_os.machine import record_observation
from delivery_os.meters import compute_m1, compute_m3, compute_scoreboard

NOW = datetime(2026, 12, 2, 12, 0, tzinfo=timezone.utc)

T2 = """---
id: C-0001
title: webhook subsystem
tier: T2
state: observe
parent: null
decider: Priya Raman
eval: evals/ok.py::test_x
behaviour_delta: "ops team stops reconciling the sheet by hand"
delta_owner: Sam Kaur
value_line: "missed events: 40/mo -> 5/mo"
kill_criterion: k
observation_date: 2020-01-01
history:
  - {state: contest, at: "2026-08-01T09:00:00+00:00", by: akp}
  - {state: commit, at: "2026-08-02T09:00:00+00:00", by: priya}
---
Events reach the endpoint reliably.
"""


@pytest.fixture
def repo(tmp_path, monkeypatch):
    acme = tmp_path / "cards" / "acme"
    acme.mkdir(parents=True)
    (acme / "C-0001.md").write_text(T2, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _card(repo: Path) -> Card:
    return load_card(repo / "cards" / "acme" / "C-0001.md")


def _observe(*flags: str) -> int:
    return main(["--root", "cards", "observe", "C-0001", "--by", "akp", *flags])


# --- the subcommand exists and writes both answers --------------------------

def test_observe_records_a_moved_value_line_on_disk(repo):
    assert _observe("--moved", "--delta-held") == 0
    assert _card(repo).value_moved is True


def test_observe_records_a_value_line_that_did_not_move(repo):
    assert _observe("--not-moved", "--delta-held") == 0
    assert _card(repo).value_moved is False


def test_observe_records_whether_the_behaviour_delta_held(repo):
    _observe("--moved", "--delta-broken")
    assert _card(repo).delta_held is False


def test_observe_appends_an_auditable_history_entry(repo):
    _observe("--moved", "--delta-broken")
    entry = _card(repo).history[-1]
    assert entry["observed"] == "moved"
    assert entry["delta"] == "broken"
    assert entry["by"] == "akp"


def test_both_answers_are_required(repo):
    # Answering only the flattering question is the M3 gaming vector.
    with pytest.raises(SystemExit):
        _observe("--moved")
    with pytest.raises(SystemExit):
        _observe("--delta-held")


def test_contradictory_flags_are_refused(repo):
    with pytest.raises(SystemExit):
        _observe("--moved", "--not-moved", "--delta-held")


def test_observe_on_an_unknown_card_is_a_clean_error(repo, capsys):
    assert main(["--root", "cards", "observe", "C-9999", "--by", "akp",
                 "--moved", "--delta-held"]) == 2
    assert "no card with id C-9999" in capsys.readouterr().err


def test_observing_before_the_date_warns_but_records(repo, capsys):
    path = repo / "cards" / "acme" / "C-0001.md"
    path.write_text(T2.replace("observation_date: 2020-01-01",
                               "observation_date: 2099-01-01"), encoding="utf-8")
    assert _observe("--moved", "--delta-held") == 0
    assert "recording early" in capsys.readouterr().err


# --- the scoreboard can now actually be fed ---------------------------------

def test_the_scoreboard_moves_because_of_the_subcommand(repo):
    before = compute_scoreboard([_card(repo)], today=date(2026, 12, 2))
    assert before["unrecorded"] == ["C-0001"] and before["headline"] is None
    _observe("--moved", "--delta-held")
    after = compute_scoreboard([_card(repo)], today=date(2026, 12, 2))
    assert after["unrecorded"] == []
    assert after["headline"] == 1.0
    assert after["moved"] == ["C-0001"]


# --- M3's guard is now implementable ----------------------------------------

def test_m3_reports_a_delta_claim_that_did_not_hold(repo):
    _observe("--moved", "--delta-broken")
    assert compute_m3([_card(repo)])["disproved"] == ["C-0001"]


def test_m3_does_not_report_a_delta_claim_that_held(repo):
    _observe("--moved", "--delta-held")
    assert compute_m3([_card(repo)])["disproved"] == []


def test_m3_reports_nothing_before_the_observation(repo):
    assert compute_m3([_card(repo)])["disproved"] == []


def test_report_renders_the_disproved_count(repo, capsys):
    _observe("--moved", "--delta-broken")
    capsys.readouterr()
    main(["--root", "cards", "report"])
    assert "delta claim disproved 1" in capsys.readouterr().out


# --- the observation entry must not be read as a state change ---------------

def test_an_observation_does_not_inflate_m1():
    # The entry carries state=<current state>. Without ANNOTATION_KEYS,
    # observing a card sitting at `commit` overwrites the commit timestamp
    # and M1 reports months of client decision latency that never happened.
    card = Card(id="C-0001", title="t", tier="T2", state="commit", parent=None,
                decider="Priya", eval="evals/ok.py::test_x", intent="x",
                history=[
                    {"state": "contest", "at": "2026-08-01T09:00:00+00:00", "by": "x"},
                    {"state": "commit", "at": "2026-08-02T09:00:00+00:00", "by": "x"},
                ])
    assert compute_m1([card], now=NOW)["median_hours"] == 24.0
    observed = record_observation(card, value_moved=True, delta_held=True,
                                  by="akp", now=NOW)
    assert compute_m1([observed], now=NOW)["median_hours"] == 24.0
