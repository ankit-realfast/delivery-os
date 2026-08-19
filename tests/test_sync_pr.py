"""CLI-level tests for `dos sync-pr` -- the path the card-sync workflow drives.

C5's guard must live here, not only in the workflow YAML: a YAML-only guard
is by construction unreachable by the test suite, which is the same shape as
the defect it is meant to prevent.
"""
from pathlib import Path

import pytest

from delivery_os.card import load_card
from delivery_os.cli import main

T2_DRAFT = """---
id: C-0001
title: webhook subsystem
tier: T2
state: draft
parent: null
decider: Priya Raman
eval: evals/C-0001_test.py::test_delivers
value_line: "missed events: 40/mo -> 5/mo"
kill_criterion: "fewer than 20 missed events per month at baseline"
observation_date: 2026-12-01
history: []
---
Events reach the client's endpoint reliably.
"""

T1_DRAFT = """---
id: C-0002
title: retry webhooks
tier: T1
state: draft
parent: C-0001
eval: evals/C-0002_test.py::test_retries
history: []
---
Failed deliveries retry three times.
"""

CHANGED = "cards/acme/C-0001-webhooks.md\ncards/acme/C-0002-retry.md"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    acme = tmp_path / "cards" / "acme"
    acme.mkdir(parents=True)
    (acme / "C-0001-webhooks.md").write_text(T2_DRAFT, encoding="utf-8")
    (acme / "C-0002-retry.md").write_text(T1_DRAFT, encoding="utf-8")
    (tmp_path / "deciders.yml").write_text('priya-r: "Priya Raman"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _sync(pr_state: str, approvers: str = "") -> int:
    return main(["--root", "cards", "sync-pr", "--changed", CHANGED,
                 "--approvers", approvers, "--pr-state", pr_state,
                 "--deciders", "deciders.yml"])


def _state(repo: Path, name: str) -> str:
    return load_card(repo / "cards" / "acme" / name).state


def _history(repo: Path, name: str) -> list[dict]:
    return load_card(repo / "cards" / "acme" / name).history


def test_open_pr_moves_a_t2_draft_into_contest(repo):
    assert _sync("open") == 0
    assert _state(repo, "C-0001-webhooks.md") == "contest"


def test_open_pr_leaves_a_t1_draft_alone(repo):
    _sync("open")
    assert _state(repo, "C-0002-retry.md") == "draft"


def test_abandoned_pr_does_not_drag_a_draft_into_contest(repo):
    # THE C5 TEST. The workflow fires on `closed` regardless of merge
    # outcome. An abandoned PR that moved this card to contest would make
    # compute_m1 emit an open_items entry whose hours grow without bound,
    # and render_report would print "waiting {hours}h on Priya Raman" --
    # naming a client-side individual for a decision never put to them.
    assert _sync("abandoned") == 0
    assert _state(repo, "C-0001-webhooks.md") == "draft"
    assert _history(repo, "C-0001-webhooks.md") == [], "nothing should have been written"


def test_abandoned_pr_writes_nothing_to_any_card_file(repo):
    before = {p: p.read_bytes() for p in (repo / "cards").rglob("*.md")}
    _sync("abandoned", approvers="priya-r")
    after = {p: p.read_bytes() for p in (repo / "cards").rglob("*.md")}
    assert before == after


def test_merged_pr_with_decider_approval_commits_the_contested_card(repo):
    _sync("open")
    assert _sync("merged", approvers="priya-r") == 0
    assert _state(repo, "C-0001-webhooks.md") == "commit"


def test_merged_pr_commits_a_t1_card_with_no_approval(repo):
    assert _sync("merged") == 0
    assert _state(repo, "C-0002-retry.md") == "commit"


def test_pr_state_is_required_not_defaulted(repo):
    # --merged was a store_true flag: absent meant "not merged", which is
    # the same lossy encoding that caused C5.
    with pytest.raises(SystemExit):
        main(["--root", "cards", "sync-pr", "--changed", CHANGED,
              "--deciders", "deciders.yml"])


def test_an_invalid_pr_state_is_refused(repo):
    with pytest.raises(SystemExit):
        main(["--root", "cards", "sync-pr", "--changed", CHANGED,
              "--pr-state", "closed", "--deciders", "deciders.yml"])
