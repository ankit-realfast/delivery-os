# Spec-as-Product Delivery OS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the minimum machinery that makes spec cards the unit of work — authored cheaply, validated automatically, moved through states with an audit trail, and reduced to four numbers — with no platform to operate.

**Architecture:** Cards are markdown files with YAML frontmatter, stored in git. Four small Python modules read them: a model/loader, a linter that encodes the tier rules, a state machine that records history, and a reporter that derives M1/M2/M3 and the scoreboard. Everything is a pure function over a list of `Card` objects, so every rule in the spec is directly unit-testable. There is no server, no database, and no UI.

**Tech Stack:** Python 3.11+, PyYAML, pytest. Nothing else. Git provides audit and storage.

**Spec:** `/Users/akp/Downloads/others/2026-08-19-spec-as-product-delivery-os-design.md`

## Global Constraints

Copied verbatim from the spec. Every task's requirements implicitly include this section.

- **"If you cannot write the eval, you do not have a spec, you have a wish."** A card without a resolvable `eval` cannot leave `contest`.
- **T1 cards carry three authored fields:** `intent`, `eval`, `blocked_on`. `blocked_on` may be empty; `intent` and `eval` may not.
- **"A card with no parent is T2 by definition."** No orphan work in the fast lane.
- **Tier is derived by the trigger test, never authored.** The `tier` field records the derived value; lint fails the card if the recorded tier is lower than the derived one. A card may never be under-tiered; over-tiering is permitted.
- **"An eval that has never been red is presumed broken until it goes red once."** Reported as a warning, never a hard failure.
- **Deliberately not measured:** per-person throughput, velocity, commits, lines, cards per week. No task may add these.
- **No purchased tooling.** No DevLake, Backstage, Copier, or radar. Runtime dependencies are PyYAML and pytest only.
- **Project root:** `/Users/akp/Downloads/delivery-os/`

---

## File Structure

| File | Responsibility |
|---|---|
| `delivery_os/card.py` | The `Card` dataclass, `STATES`, and `load_card` / `load_all`. Nothing else knows the file format. |
| `delivery_os/lint.py` | `Finding`, `T2_TRIGGERS`, `required_tier`, `lint_card`. Encodes spec §3 and §4. Pure functions. |
| `delivery_os/machine.py` | `LEGAL_TRANSITIONS`, `move_card`, `record_verify`. Owns history and the red-eval fork. |
| `delivery_os/meters.py` | `compute_m1`, `compute_m2`, `compute_m3`, `compute_scoreboard`. Pure functions over `list[Card]`. |
| `delivery_os/cli.py` | `card-new`, `card-lint`, `card-move`, `card-verify`, `report`. Thin argparse shell; no logic. |
| `templates/card-t1.md`, `templates/card-t2.md` | Authoring templates. Keep card-writing near-free. |
| `contract/decider-clause.md`, `contract/reciprocal-sla.md` | Commercial layer (spec §6). |
| `cards/<engagement>/C-NNNN-<slug>.md` | The cards themselves. |
| `tests/` | One test module per source module. |

Split by responsibility: format knowledge lives only in `card.py`, policy only in `lint.py`, time and history only in `machine.py`, arithmetic only in `meters.py`. That boundary is what makes every spec rule testable in isolation.

---

## Task 1: Card model and loader

**Files:**
- Create: `delivery_os/__init__.py`
- Create: `delivery_os/card.py`
- Create: `tests/test_card.py`
- Create: `pyproject.toml`

**Interfaces:**
- Consumes: nothing
- Produces: `Card` dataclass; `STATES: list[str]`; `state_index(state: str) -> int`; `load_card(path: str | Path) -> Card`; `load_all(root: str | Path) -> list[Card]`

- [ ] **Step 1: Create the project skeleton**

```bash
mkdir -p /Users/akp/Downloads/delivery-os/{delivery_os,tests,templates,contract,cards}
cd /Users/akp/Downloads/delivery-os
git init
python3 -m venv .venv && .venv/bin/pip install pyyaml pytest
touch delivery_os/__init__.py
```

Write `pyproject.toml`:

```toml
[project]
name = "delivery-os"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pyyaml>=6.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_card.py`:

```python
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
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd /Users/akp/Downloads/delivery-os && .venv/bin/pytest tests/test_card.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'delivery_os.card'`

- [ ] **Step 4: Write the minimal implementation**

Create `delivery_os/card.py`:

```python
from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

STATES = ["draft", "contest", "commit", "build", "verify", "observe", "closed"]


def state_index(state: str) -> int:
    return STATES.index(state)


@dataclass
class Card:
    id: str
    title: str
    tier: str
    state: str
    path: Path | None = None
    parent: str | None = None
    decider: str | None = None
    eval: str | None = None
    behaviour_delta: str = "none"
    delta_owner: str | None = None
    value_line: str | None = None
    kill_criterion: str | None = None
    observation_date: date | None = None
    blocked_on: str | None = None
    touches_production_data: bool = False
    touches_auth: bool = False
    external_commitment: bool = False
    flag_off: bool = True
    value_moved: bool | None = None
    history: list[dict] = field(default_factory=list)
    intent: str = ""


_FIELD_NAMES = {f.name for f in dataclasses.fields(Card)}
# Loader-owned: derived from the file itself, never authored in frontmatter.
_LOADER_OWNED = {"path", "intent"}
_AUTHORABLE = _FIELD_NAMES - _LOADER_OWNED
# Line-anchored: a bare `---` line only. Free-text fields legitimately
# contain "---" (horizontal rules, em-dashes, pasted text).
_FRONTMATTER_RE = re.compile(r"(?m)^---\s*$")


def load_card(path: str | Path) -> Card:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    parts = _FRONTMATTER_RE.split(text, maxsplit=2)
    if len(parts) < 3 or parts[0].strip():
        raise ValueError(f"{path}: missing or unterminated YAML frontmatter")
    _, front, body = parts
    data = yaml.safe_load(front) or {}
    unknown = sorted(set(data) - _AUTHORABLE)
    if unknown:
        raise ValueError(f"{path}: unknown fields {unknown}")
    data["path"] = path
    data["intent"] = body.strip()
    return Card(**data)


def load_all(root: str | Path) -> list[Card]:
    cards = [load_card(p) for p in sorted(Path(root).rglob("*.md"))]
    return sorted(cards, key=lambda c: c.id)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_card.py -v`
Expected: PASS — 6 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml delivery_os/ tests/test_card.py
git commit -m "feat: card model and loader"
```

---

## Task 2: Lint — required fields by tier

**Files:**
- Create: `delivery_os/lint.py`
- Create: `tests/test_lint_fields.py`

**Interfaces:**
- Consumes: `Card`, `STATES` from `delivery_os.card`
- Produces: `Finding(card_id: str, rule: str, message: str)`; `T1_REQUIRED: list[str]`; `T2_REQUIRED: list[str]`; `lint_card(card: Card) -> list[Finding]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_lint_fields.py`:

```python
from datetime import date

from delivery_os.card import Card
from delivery_os.lint import Finding, lint_card


def t1(**kw) -> Card:
    base = dict(
        id="C-0002", title="t", tier="T1", state="draft", parent="C-0001",
        eval="evals/C-0002_test.py::test_x",
    )
    base.update(kw)
    return Card(intent="something is true", **base)


def t2(**kw) -> Card:
    base = dict(
        id="C-0001", title="t", tier="T2", state="draft", parent=None,
        decider="Priya Raman", eval="evals/C-0001_test.py::test_x",
        value_line="tickets: 40/mo -> 5/mo", kill_criterion="baseline under 20",
        observation_date=date(2026, 9, 30), touches_production_data=True,
    )
    base.update(kw)
    return Card(intent="something is true", **base)


def rules(findings: list[Finding]) -> set[str]:
    return {f.rule for f in findings}


def test_complete_t1_card_is_clean():
    assert lint_card(t1()) == []


def test_complete_t2_card_is_clean():
    assert lint_card(t2()) == []


def test_t1_without_eval_is_a_wish_not_a_spec():
    findings = lint_card(t1(eval=None))
    assert "missing-field" in rules(findings)
    assert any("eval" in f.message for f in findings)


def test_t1_without_intent_is_rejected():
    assert "missing-field" in rules(lint_card(t1(intent="")))


def test_t1_with_empty_blocked_on_is_fine():
    assert lint_card(t1(blocked_on=None)) == []


def test_t2_missing_kill_criterion_is_rejected():
    findings = lint_card(t2(kill_criterion=None))
    assert any("kill_criterion" in f.message for f in findings)


def test_t2_missing_observation_date_is_rejected():
    findings = lint_card(t2(observation_date=None))
    assert any("observation_date" in f.message for f in findings)


def test_t2_missing_value_line_is_rejected():
    findings = lint_card(t2(value_line=None))
    assert any("value_line" in f.message for f in findings)


def test_unknown_state_is_rejected():
    assert "bad-state" in rules(lint_card(t1(state="in_progress")))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_lint_fields.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'delivery_os.lint'`

- [ ] **Step 3: Write the minimal implementation**

Create `delivery_os/lint.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from delivery_os.card import Card, STATES

T1_REQUIRED = ["intent", "eval", "parent"]
T2_REQUIRED = [
    "intent", "eval", "decider", "value_line", "kill_criterion", "observation_date",
]


@dataclass(frozen=True)
class Finding:
    card_id: str
    rule: str
    message: str


def lint_card(card: Card) -> list[Finding]:
    findings: list[Finding] = []

    if card.state not in STATES:
        findings.append(Finding(card.id, "bad-state", f"unknown state '{card.state}'"))

    required = T2_REQUIRED if card.tier == "T2" else T1_REQUIRED
    for name in required:
        if not getattr(card, name, None):
            findings.append(
                Finding(card.id, "missing-field", f"{card.tier} card requires '{name}'")
            )

    return findings
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_lint_fields.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: Commit**

```bash
git add delivery_os/lint.py tests/test_lint_fields.py
git commit -m "feat: lint required card fields by tier"
```

---

## Task 3: Lint — tier escalation triggers

This task encodes spec §4: the five automatic T2 triggers plus the orphan rule. It is the mechanism that makes under-tiering impossible.

**Files:**
- Modify: `delivery_os/lint.py`
- Create: `tests/test_lint_tier.py`

**Interfaces:**
- Consumes: `Card` from `delivery_os.card`
- Produces: `T2_TRIGGERS: list[tuple[str, Callable[[Card], bool], str]]`; `required_tier(card: Card) -> str`; `lint_card` gains rule `tier-escalation` and rule `unowned-delta`

- [ ] **Step 1: Write the failing test**

Create `tests/test_lint_tier.py`:

```python
from delivery_os.card import Card
from delivery_os.lint import lint_card, required_tier


def card(**kw) -> Card:
    base = dict(
        id="C-0002", title="t", tier="T1", state="draft", parent="C-0001",
        eval="evals/C-0002_test.py::test_x",
    )
    base.update(kw)
    return Card(intent="something is true", **base)


def rules(findings) -> set[str]:
    return {f.rule for f in findings}


def test_plain_reversible_card_stays_t1():
    assert required_tier(card()) == "T1"


def test_orphan_card_is_t2_by_definition():
    assert required_tier(card(parent=None)) == "T2"
    assert "tier-escalation" in rules(lint_card(card(parent=None)))


def test_nonzero_behaviour_delta_forces_t2():
    c = card(behaviour_delta="ops team stops using the old sheet", delta_owner="Sam")
    assert required_tier(c) == "T2"


def test_unflaggable_card_forces_t2():
    assert required_tier(card(flag_off=False)) == "T2"


def test_production_data_shape_forces_t2():
    assert required_tier(card(touches_production_data=True)) == "T2"


def test_auth_forces_t2():
    assert required_tier(card(touches_auth=True)) == "T2"


def test_external_commitment_forces_t2():
    assert required_tier(card(external_commitment=True)) == "T2"


def test_escalation_message_names_every_reason():
    findings = lint_card(card(parent=None, touches_auth=True))
    msg = next(f.message for f in findings if f.rule == "tier-escalation")
    assert "no parent" in msg
    assert "auth" in msg


def test_over_tiering_is_allowed():
    c = card(tier="T2", parent="C-0001", decider="P", value_line="v",
             kill_criterion="k", observation_date="2026-09-30")
    assert "tier-escalation" not in rules(lint_card(c))


def test_nonzero_delta_without_owner_is_flagged():
    c = card(tier="T2", parent="C-0001", decider="P", value_line="v",
             kill_criterion="k", observation_date="2026-09-30",
             behaviour_delta="ops team stops using the old sheet")
    assert "unowned-delta" in rules(lint_card(c))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_lint_tier.py -v`
Expected: FAIL — `ImportError: cannot import name 'required_tier' from 'delivery_os.lint'`

- [ ] **Step 3: Add triggers and escalation to `delivery_os/lint.py`**

Insert after the `T2_REQUIRED` definition:

```python
T2_TRIGGERS = [
    ("orphan", lambda c: c.parent is None, "card has no parent"),
    ("behaviour-delta", lambda c: c.behaviour_delta != "none", "behaviour delta is not none"),
    ("no-flag", lambda c: not c.flag_off, "cannot be switched off with a flag"),
    ("production-data", lambda c: c.touches_production_data, "changes the shape of production data"),
    ("auth", lambda c: c.touches_auth, "touches auth, permissions, or security posture"),
    ("external-commitment", lambda c: c.external_commitment, "creates an external commitment"),
]


def required_tier(card: Card) -> str:
    return "T2" if any(pred(card) for _, pred, _ in T2_TRIGGERS) else "T1"
```

Then insert into `lint_card`, immediately after the `bad-state` check:

```python
    if required_tier(card) == "T2" and card.tier != "T2":
        reasons = "; ".join(msg for _, pred, msg in T2_TRIGGERS if pred(card))
        findings.append(Finding(card.id, "tier-escalation", f"must be T2: {reasons}"))

    if card.behaviour_delta != "none" and not card.delta_owner:
        findings.append(
            Finding(card.id, "unowned-delta", "non-zero behaviour delta requires delta_owner")
        )
```

- [ ] **Step 4: Run the full lint suite**

Run: `.venv/bin/pytest tests/test_lint_tier.py tests/test_lint_fields.py -v`
Expected: PASS — 19 passed

- [ ] **Step 5: Commit**

```bash
git add delivery_os/lint.py tests/test_lint_tier.py
git commit -m "feat: tier escalation triggers and orphan rule"
```

---

## Task 4: State machine with history

**Files:**
- Create: `delivery_os/machine.py`
- Create: `tests/test_machine.py`

**Interfaces:**
- Consumes: `Card`, `STATES` from `delivery_os.card`
- Produces: `LEGAL_TRANSITIONS: dict[str, list[str]]`; `IllegalTransition(Exception)`; `move_card(card: Card, to_state: str, by: str, now: datetime) -> Card`; `record_verify(card: Card, passed: bool, by: str, now: datetime) -> Card`

- [ ] **Step 1: Write the failing test**

Create `tests/test_machine.py`:

```python
from datetime import datetime, timezone

import pytest

from delivery_os.card import Card
from delivery_os.machine import IllegalTransition, move_card, record_verify

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def card(state="draft", **kw) -> Card:
    base = dict(id="C-0002", title="t", tier="T1", state=state, parent="C-0001",
                eval="evals/C-0002_test.py::test_x")
    base.update(kw)
    return Card(intent="x", **base)


def test_move_appends_history_and_sets_state():
    moved = move_card(card(), "contest", by="akp", now=NOW)
    assert moved.state == "contest"
    assert moved.history[-1] == {"state": "contest", "at": "2026-08-19T12:00:00+00:00", "by": "akp"}


def test_move_does_not_mutate_the_original():
    original = card()
    move_card(original, "contest", by="akp", now=NOW)
    assert original.state == "draft"
    assert original.history == []


def test_t1_card_skips_contest_entirely():
    # Spec 4: "T1 - reversible. No contest." A T1 card needs no client decision.
    assert move_card(card("draft", tier="T1"), "commit", by="akp", now=NOW).state == "commit"


def test_t2_card_may_not_skip_contest():
    with pytest.raises(IllegalTransition, match="draft -> commit"):
        move_card(card("draft", tier="T2"), "commit", by="akp", now=NOW)


def test_illegal_transition_is_refused():
    with pytest.raises(IllegalTransition, match="commit -> observe"):
        move_card(card("commit"), "observe", by="akp", now=NOW)


def test_contest_can_return_to_draft():
    assert move_card(card("contest"), "draft", by="akp", now=NOW).state == "draft"


def test_verify_failure_with_wrong_build_goes_back_to_build():
    assert move_card(card("verify"), "build", by="akp", now=NOW).state == "build"


def test_verify_failure_with_right_build_goes_back_to_contest():
    assert move_card(card("verify"), "contest", by="akp", now=NOW).state == "contest"


def test_record_verify_writes_pass_into_history():
    c = record_verify(card("verify"), passed=True, by="ci", now=NOW)
    assert c.history[-1]["verify"] == "pass"
    assert c.state == "verify"


def test_record_verify_writes_fail_into_history():
    c = record_verify(card("verify"), passed=False, by="ci", now=NOW)
    assert c.history[-1]["verify"] == "fail"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_machine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'delivery_os.machine'`

- [ ] **Step 3: Write the minimal implementation**

Create `delivery_os/machine.py`:

```python
from __future__ import annotations

import dataclasses
from datetime import datetime

from delivery_os.card import Card

LEGAL_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["contest"],
    "contest": ["commit", "draft"],
    "commit": ["build"],
    "build": ["verify"],
    # The red-eval fork: build wrong -> build; spec wrong -> contest.
    "verify": ["observe", "build", "contest"],
    "observe": ["closed"],
    "closed": [],
}


class IllegalTransition(Exception):
    pass


def move_card(card: Card, to_state: str, by: str, now: datetime) -> Card:
    legal = list(LEGAL_TRANSITIONS.get(card.state, []))
    if card.tier == "T1" and card.state == "draft":
        legal.append("commit")  # spec 4: T1 has no contest
    if to_state not in legal:
        raise IllegalTransition(f"{card.state} -> {to_state}")
    entry = {"state": to_state, "at": now.isoformat(), "by": by}
    return dataclasses.replace(
        card, state=to_state, history=[*card.history, entry]
    )


def record_verify(card: Card, passed: bool, by: str, now: datetime) -> Card:
    entry = {
        "state": card.state,
        "at": now.isoformat(),
        "by": by,
        "verify": "pass" if passed else "fail",
    }
    return dataclasses.replace(card, history=[*card.history, entry])
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_machine.py -v`
Expected: PASS — 10 passed

- [ ] **Step 5: Commit**

```bash
git add delivery_os/machine.py tests/test_machine.py
git commit -m "feat: card state machine with history and red-eval fork"
```

---

## Task 5: Meters M1, M2, M3

**Files:**
- Create: `delivery_os/meters.py`
- Create: `tests/test_meters.py`

**Interfaces:**
- Consumes: `Card`, `state_index` from `delivery_os.card`
- Produces: `compute_m1(cards, now) -> dict`; `compute_m2(cards) -> dict`; `compute_m3(cards) -> dict`. Each returns a dict with a `headline` key plus rule-specific detail keys documented in the tests below.

- [ ] **Step 1: Write the failing test**

Create `tests/test_meters.py`:

```python
from datetime import datetime, timezone

from delivery_os.card import Card
from delivery_os.meters import compute_m1, compute_m2, compute_m3

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def card(**kw) -> Card:
    base = dict(id="C-0001", title="t", tier="T1", state="draft", parent="C-0000",
                eval="evals/x_test.py::test_x")
    base.update(kw)
    return Card(intent="x", **base)


def hist(*pairs):
    return [{"state": s, "at": at, "by": "x"} for s, at in pairs]


def test_m1_measures_contest_to_commit_in_hours():
    c = card(state="commit", decider="Priya", history=hist(
        ("contest", "2026-08-01T09:00:00+00:00"),
        ("commit", "2026-08-02T09:00:00+00:00"),
    ))
    m1 = compute_m1([c], now=NOW)
    assert m1["median_hours"] == 24.0
    assert m1["by_decider"]["Priya"] == 24.0


def test_m1_reports_open_cards_aging_in_contest():
    c = card(state="contest", decider="Priya", history=hist(
        ("contest", "2026-08-18T12:00:00+00:00"),
    ))
    m1 = compute_m1([c], now=NOW)
    assert m1["open"] == [{"id": "C-0001", "decider": "Priya", "hours": 24.0}]
    assert m1["median_hours"] is None


def test_m1_uses_the_last_contest_entry_when_a_card_bounced():
    c = card(state="commit", decider="Priya", history=hist(
        ("contest", "2026-08-01T09:00:00+00:00"),
        ("draft", "2026-08-01T10:00:00+00:00"),
        ("contest", "2026-08-02T09:00:00+00:00"),
        ("commit", "2026-08-02T15:00:00+00:00"),
    ))
    assert compute_m1([c], now=NOW)["median_hours"] == 6.0


def test_m2_counts_only_cards_at_commit_or_later():
    drafted = card(id="C-0001", state="draft", eval=None)
    committed = card(id="C-0002", state="commit")
    m2 = compute_m2([drafted, committed])
    assert m2["in_scope"] == 1
    assert m2["with_eval"] == 1
    assert m2["headline"] == 1.0


def test_m2_flags_evals_that_have_never_been_red():
    never_red = card(id="C-0001", state="verify", history=[
        {"state": "verify", "at": "2026-08-01T09:00:00+00:00", "by": "ci", "verify": "pass"},
    ])
    been_red = card(id="C-0002", state="verify", history=[
        {"state": "verify", "at": "2026-08-01T09:00:00+00:00", "by": "ci", "verify": "fail"},
        {"state": "verify", "at": "2026-08-01T10:00:00+00:00", "by": "ci", "verify": "pass"},
    ])
    assert compute_m2([never_red, been_red])["never_red"] == ["C-0001"]


def test_m2_missing_eval_lowers_the_headline():
    m2 = compute_m2([card(id="C-0001", state="commit", eval=None),
                     card(id="C-0002", state="commit")])
    assert m2["headline"] == 0.5
    assert m2["without_eval"] == ["C-0001"]


def test_m3_counts_live_nonzero_deltas_and_names_the_unowned():
    owned = card(id="C-0001", state="build", tier="T2",
                 behaviour_delta="ops stops using the sheet", delta_owner="Sam")
    unowned = card(id="C-0002", state="build", tier="T2",
                   behaviour_delta="finance re-codes invoices")
    closed = card(id="C-0003", state="closed", tier="T2",
                  behaviour_delta="already absorbed", delta_owner="Sam")
    m3 = compute_m3([owned, unowned, closed])
    assert m3["live_deltas"] == 2
    assert m3["unowned"] == ["C-0002"]


def test_m3_is_zero_when_every_card_absorbed_the_process():
    assert compute_m3([card(state="build")])["live_deltas"] == 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_meters.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'delivery_os.meters'`

- [ ] **Step 3: Write the minimal implementation**

Create `delivery_os/meters.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_meters.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
git add delivery_os/meters.py tests/test_meters.py
git commit -m "feat: meters M1 decision latency, M2 eval coverage, M3 behaviour-delta debt"
```

---

## Task 6: The scoreboard and observation-due list

Kept separate from the meters on purpose: spec §5 requires the output number to live in its own box, never mixed with the constraint meters.

**Files:**
- Modify: `delivery_os/meters.py`
- Create: `tests/test_scoreboard.py`

**Interfaces:**
- Consumes: `Card` from `delivery_os.card`
- Produces: `compute_scoreboard(cards: list[Card], today: date) -> dict` with keys `headline`, `due`, `unrecorded`, `moved`, `not_moved`

- [ ] **Step 1: Write the failing test**

Create `tests/test_scoreboard.py`:

```python
from datetime import date

from delivery_os.card import Card
from delivery_os.meters import compute_scoreboard

TODAY = date(2026, 10, 1)


def t2(**kw) -> Card:
    base = dict(id="C-0001", title="t", tier="T2", state="observe", parent=None,
                decider="Priya", eval="evals/x_test.py::test_x",
                value_line="tickets: 40/mo -> 5/mo", kill_criterion="k",
                observation_date=date(2026, 9, 30))
    base.update(kw)
    return Card(intent="x", **base)


def test_card_before_its_observation_date_is_not_due():
    sb = compute_scoreboard([t2(observation_date=date(2026, 12, 1))], today=TODAY)
    assert sb["due"] == []
    assert sb["headline"] is None


def test_due_card_without_a_recorded_outcome_is_chased_not_scored():
    sb = compute_scoreboard([t2(value_moved=None)], today=TODAY)
    assert sb["unrecorded"] == ["C-0001"]
    assert sb["headline"] is None


def test_headline_is_share_of_recorded_cards_whose_value_line_moved():
    cards = [
        t2(id="C-0001", value_moved=True),
        t2(id="C-0002", value_moved=True),
        t2(id="C-0003", value_moved=False),
    ]
    sb = compute_scoreboard(cards, today=TODAY)
    assert sb["headline"] == 0.67
    assert sb["moved"] == ["C-0001", "C-0002"]
    assert sb["not_moved"] == ["C-0003"]


def test_t1_cards_never_enter_the_scoreboard():
    inherited = Card(id="C-0009", title="t", tier="T1", state="observe",
                     parent="C-0001", eval="evals/x_test.py::test_x",
                     observation_date=date(2026, 9, 1), value_moved=True, intent="x")
    assert compute_scoreboard([inherited], today=TODAY)["due"] == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_scoreboard.py -v`
Expected: FAIL — `ImportError: cannot import name 'compute_scoreboard'`

- [ ] **Step 3: Append to `delivery_os/meters.py`**

```python
def compute_scoreboard(cards: list[Card], today) -> dict:
    due = [
        c for c in cards
        if c.tier == "T2" and c.observation_date and c.observation_date <= today
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
```

Add `from datetime import date` is not required — `today` is compared against `card.observation_date` directly.

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_scoreboard.py -v`
Expected: PASS — 4 passed

- [ ] **Step 5: Commit**

```bash
git add delivery_os/meters.py tests/test_scoreboard.py
git commit -m "feat: value-line scoreboard and observation-due list"
```

---

## Task 7: CLI and authoring templates

Card authoring must stay near-free or the OS silts up. This task is what keeps it cheap.

**Files:**
- Create: `delivery_os/cli.py`
- Create: `templates/card-t1.md`
- Create: `templates/card-t2.md`
- Create: `tests/test_cli.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: everything above
- Produces: `next_card_id(root) -> str`; `new_card(root, engagement, title, tier, parent) -> Path`; `render_report(cards, now, today) -> str`; console script `dos`

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli.py`:

```python
from datetime import date, datetime, timezone
from pathlib import Path

from delivery_os.card import load_card
from delivery_os.cli import new_card, next_card_id, render_report

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def test_next_card_id_starts_at_one(tmp_path):
    assert next_card_id(tmp_path) == "C-0001"


def test_next_card_id_increments_past_the_highest(tmp_path):
    new_card(tmp_path, "acme", "first thing", tier="T2", parent=None)
    new_card(tmp_path, "acme", "second thing", tier="T1", parent="C-0001")
    assert next_card_id(tmp_path) == "C-0003"


def test_new_t1_card_is_three_authored_fields(tmp_path):
    path = new_card(tmp_path, "acme", "retry webhooks", tier="T1", parent="C-0001")
    card = load_card(path)
    assert card.tier == "T1"
    assert card.parent == "C-0001"
    assert card.state == "draft"
    assert card.eval is None
    assert path.name == "C-0001-retry-webhooks.md"


def test_new_orphan_card_is_written_as_t2(tmp_path):
    path = new_card(tmp_path, "acme", "webhook subsystem", tier="T1", parent=None)
    assert load_card(path).tier == "T2"


def test_report_renders_all_four_numbers(tmp_path):
    new_card(tmp_path, "acme", "webhook subsystem", tier="T2", parent=None)
    cards = [load_card(p) for p in Path(tmp_path).rglob("*.md")]
    out = render_report(cards, now=NOW, today=date(2026, 8, 19))
    assert "M1 decision latency" in out
    assert "M2 eval coverage" in out
    assert "M3 behaviour-delta debt" in out
    assert "SCOREBOARD" in out
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'delivery_os.cli'`

- [ ] **Step 3: Write the templates**

Create `templates/card-t1.md`:

```markdown
---
id: {id}
title: {title}
tier: T1
state: draft
parent: {parent}
eval: null
blocked_on: null
history: []
---
{title}
```

Create `templates/card-t2.md`:

```markdown
---
id: {id}
title: {title}
tier: T2
state: draft
parent: {parent}
decider: null
eval: null
behaviour_delta: none
delta_owner: null
value_line: null
kill_criterion: null
observation_date: null
blocked_on: null
touches_production_data: false
touches_auth: false
external_commitment: false
flag_off: true
value_moved: null
history: []
---
{title}
```

- [ ] **Step 4: Write the implementation**

Create `delivery_os/cli.py`:

```python
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from delivery_os.card import load_all, load_card
from delivery_os.lint import lint_card, required_tier
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
    body = template.format(id=card_id, title=title, parent=parent or "null")
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="dos")
    parser.add_argument("--root", default="cards")
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
```

Add to `pyproject.toml`:

```toml
[project.scripts]
dos = "delivery_os.cli:main"
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_cli.py -v`
Expected: PASS — 5 passed

- [ ] **Step 6: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: PASS — 52 passed

- [ ] **Step 7: Commit**

```bash
git add delivery_os/cli.py templates/ tests/test_cli.py pyproject.toml
git commit -m "feat: card authoring CLI, templates, and four-number report"
```

---

## Task 8: Lint in CI

Conformance is an eval, not a portal. This is the whole of spec slot 3.

**Files:**
- Create: `.github/workflows/cards.yml`
- Create: `tests/test_lint_repo.py`

**Interfaces:**
- Consumes: `load_all`, `lint_card`
- Produces: a failing CI job when any card in the repo is invalid

- [ ] **Step 1: Write the failing test**

Create `tests/test_lint_repo.py`:

```python
from pathlib import Path

from delivery_os.card import load_all
from delivery_os.lint import lint_card

REPO_CARDS = Path(__file__).resolve().parent.parent / "cards"


def test_every_card_in_the_repo_is_valid():
    findings = [f for c in load_all(REPO_CARDS) for f in lint_card(c)]
    assert findings == [], "\n".join(f"{f.card_id} {f.rule}: {f.message}" for f in findings)
```

- [ ] **Step 2: Run it to verify it passes on an empty card set**

Run: `.venv/bin/pytest tests/test_lint_repo.py -v`
Expected: PASS — the `cards/` directory is empty, so there is nothing to violate.

- [ ] **Step 3: Prove the test can fail**

An eval that has never been red is presumed broken. Create a deliberately invalid card, confirm the test goes red, then delete it:

```bash
mkdir -p cards/scratch
printf -- '---\nid: C-9999\ntitle: bad\ntier: T1\nstate: draft\nparent: null\neval: null\n---\nx\n' > cards/scratch/C-9999-bad.md
.venv/bin/pytest tests/test_lint_repo.py -v   # expected: FAIL, tier-escalation + missing-field
rm -rf cards/scratch
.venv/bin/pytest tests/test_lint_repo.py -v   # expected: PASS
```

- [ ] **Step 4: Add the CI workflow**

Create `.github/workflows/cards.yml`:

```yaml
name: cards
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e . pytest
      - run: pytest -v
      - run: python -m delivery_os.cli --root cards lint
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/cards.yml tests/test_lint_repo.py
git commit -m "ci: fail the build on any invalid card"
```

---

## Task 9: The commercial layer

**This is the only task with no automated test.** Its acceptance is a human review gate, stated explicitly below. It implements spec §6, which no amount of Python can implement.

**Files:**
- Create: `contract/decider-clause.md`
- Create: `contract/reciprocal-sla.md`
- Create: `templates/handover-card.md`

**Interfaces:**
- Consumes: M1 from `delivery_os.meters` as the measurement referenced by the SLA
- Produces: clause text for the next SOW; a handover card template whose eval is the client's own CI

- [ ] **Step 1: Write the Decider clause**

Create `contract/decider-clause.md`:

```markdown
# Named Decider clause

**Purpose.** Spec §5: "Naming them in the contract is the single highest-leverage
clause available." Without a named Decider, M1 is unattributable and the delivery
commitment in the reciprocal SLA cannot be honestly offered.

## Clause text

The Client shall nominate, in writing, one **Named Decider** per workstream, being
an individual with authority to approve scope and accept delivery without further
internal escalation. The Client may substitute the Named Decider on five business
days' written notice.

Where a decision item is presented to the Named Decider and remains unresolved
beyond the Decision Window defined in Schedule A, the corresponding Delivery
Window in Schedule A is extended by the period of that delay, and the Supplier's
delivery commitments are suspended in respect of the affected items only.

Decision items, their presentation timestamps, and their resolution timestamps
are recorded in the shared card repository and are available to both parties.

## Why this is not administrative

Half the delivery clock sits inside the Client's organisation. Without this clause,
a late engagement produces an unwinnable argument, because nobody instrumented
whose clock ran out.
```

- [ ] **Step 2: Write the reciprocal SLA**

Create `contract/reciprocal-sla.md`:

```markdown
# Schedule A — Reciprocal delivery and decision windows

| Party | Commitment | Measured by |
|---|---|---|
| Supplier | Committed cards move Commit to Verify within **N** business days | Card history timestamps |
| Client | Cards in Contest are resolved by the Named Decider within **M** business days | M1 |

Breach of the Client commitment suspends the Supplier commitment for the affected
cards, automatically and visibly, without notice or dispute.

**N and M are deliberately unset (spec §9, U2).** Provisional values of N = 5 and
M = 3 business days apply to the first engagement, to be replaced by the observed
Commit-to-Verify and Contest-to-Commit distributions after fifty cards.

Reporting: the `dos report` output is shared with the Client at the agreed cadence.
It contains M1, M2, M3, and the scoreboard, and contains no per-person throughput
measure of any kind.
```

- [ ] **Step 3: Write the handover card template**

Create `templates/handover-card.md`:

```markdown
---
id: {id}
title: capability transfer to {client}
tier: T2
state: draft
parent: null
decider: null
eval: evals/handover_test.py::test_suite_green_in_client_ci
behaviour_delta: none
delta_owner: null
value_line: "engagements requiring supplier intervention post-exit: 0"
kill_criterion: "client has no named operator by the observation date"
observation_date: null
blocked_on: null
touches_production_data: false
touches_auth: false
external_commitment: true
flag_off: false
value_moved: null
history: []
---
The full card corpus and eval suite run green in {client}'s own CI, executed by
{client}'s named operator, with no supplier involvement in the run.
```

- [ ] **Step 4: Human review gate (no automated test exists for this task)**

Acceptance requires all three:

1. A legal read of `contract/decider-clause.md` and `contract/reciprocal-sla.md` has been completed and any redlines applied.
2. The Named Decider clause appears in the next SOW draft.
3. A named person has accepted ownership of setting N and M after fifty cards.

If item 2 is refused by a client, that resolves spec §9 U3 negatively — and the speed-of-execution positioning cannot be honestly made. **Escalate rather than proceed.**

- [ ] **Step 5: Commit**

```bash
git add contract/ templates/handover-card.md
git commit -m "feat: named-Decider clause, reciprocal SLA, handover card template"
```

---

## Task 10: PR-merge automation

The Contest state **is** a pull request. This task makes that literal: opening a PR moves its cards to `contest`, and merging moves them to `commit` — but a **T2 card only reaches `commit` if the named Decider is among the PR approvers.** That single rule is what makes M1 measure the actual named human rather than whoever clicked last, and it is what makes the reciprocal SLA in Task 9 enforceable.

**Files:**
- Create: `delivery_os/gh.py`
- Create: `tests/test_gh.py`
- Create: `contract/deciders.yml`
- Modify: `delivery_os/cli.py` (add the `sync-pr` subcommand)
- Create: `.github/workflows/card-sync.yml`

**Interfaces:**
- Consumes: `Card` from `delivery_os.card`; `move_card` from `delivery_os.machine`; `load_all`, `_rewrite` from earlier tasks
- Produces: `card_ids_in_paths(paths: list[str]) -> list[str]`; `load_deciders(path) -> dict[str, str]`; `decider_approved(card: Card, approvers: list[str], deciders: dict[str, str]) -> bool`; `transition_for(card: Card, merged: bool, approvers: list[str], deciders: dict[str, str]) -> str | None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_gh.py`:

```python
from delivery_os.card import Card
from delivery_os.gh import (
    card_ids_in_paths,
    decider_approved,
    load_deciders,
    transition_for,
)

DECIDERS = {"priya-r": "Priya Raman <priya@client.example>", "sam-k": "Sam Kaur"}


def card(**kw) -> Card:
    base = dict(id="C-0007", title="t", tier="T2", state="contest", parent=None,
                decider="Priya Raman <priya@client.example>",
                eval="evals/C-0007_test.py::test_x")
    base.update(kw)
    return Card(intent="x", **base)


def test_card_ids_are_extracted_from_changed_paths():
    paths = ["cards/acme/C-0007-webhooks.md", "cards/acme/C-0008-retry.md"]
    assert card_ids_in_paths(paths) == ["C-0007", "C-0008"]


def test_non_card_files_are_ignored():
    paths = ["README.md", "delivery_os/cli.py", "docs/C-9999-notes.txt"]
    assert card_ids_in_paths(paths) == []


def test_duplicate_ids_are_collapsed():
    assert card_ids_in_paths(["cards/a/C-0007-x.md", "cards/b/C-0007-x.md"]) == ["C-0007"]


def test_deciders_file_maps_handles_to_decider_strings(tmp_path):
    f = tmp_path / "deciders.yml"
    f.write_text('priya-r: "Priya Raman <priya@client.example>"\n', encoding="utf-8")
    assert load_deciders(f) == {"priya-r": "Priya Raman <priya@client.example>"}


def test_decider_approval_matches_through_the_handle_mapping():
    assert decider_approved(card(), ["priya-r"], DECIDERS) is True


def test_approval_by_someone_else_is_not_the_decider():
    assert decider_approved(card(), ["sam-k", "random-dev"], DECIDERS) is False


def test_unknown_handle_is_ignored_not_trusted():
    assert decider_approved(card(), ["ghost"], DECIDERS) is False


def test_open_pr_moves_a_t2_draft_into_contest():
    assert transition_for(card(state="draft"), merged=False, approvers=[], deciders=DECIDERS) == "contest"


def test_merged_pr_with_decider_approval_commits_a_t2_card():
    assert transition_for(card(), merged=True, approvers=["priya-r"], deciders=DECIDERS) == "commit"


def test_merged_pr_without_decider_approval_does_not_commit():
    assert transition_for(card(), merged=True, approvers=["sam-k"], deciders=DECIDERS) is None


def test_t1_card_commits_on_merge_with_no_approval_needed():
    t1 = card(id="C-0008", tier="T1", state="draft", parent="C-0007", decider=None)
    assert transition_for(t1, merged=True, approvers=[], deciders=DECIDERS) == "commit"


def test_t1_card_is_not_dragged_into_contest_by_an_open_pr():
    t1 = card(id="C-0008", tier="T1", state="draft", parent="C-0007", decider=None)
    assert transition_for(t1, merged=False, approvers=[], deciders=DECIDERS) is None


def test_card_already_past_commit_is_left_alone():
    assert transition_for(card(state="build"), merged=True, approvers=["priya-r"], deciders=DECIDERS) is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_gh.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'delivery_os.gh'`

- [ ] **Step 3: Write the implementation**

Create `delivery_os/gh.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

import yaml

from delivery_os.card import Card

CARD_RE = re.compile(r"(C-\d{4})")


def card_ids_in_paths(paths: list[str]) -> list[str]:
    found: list[str] = []
    for raw in paths:
        path = Path(raw)
        if path.suffix != ".md" or "cards" not in path.parts[:-1]:
            continue
        match = CARD_RE.match(path.name)
        if match and match.group(1) not in found:
            found.append(match.group(1))
    return found


def load_deciders(path: str | Path) -> dict[str, str]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def decider_approved(card: Card, approvers: list[str], deciders: dict[str, str]) -> bool:
    if not card.decider:
        return False
    return any(deciders.get(handle) == card.decider for handle in approvers)


def transition_for(
    card: Card, merged: bool, approvers: list[str], deciders: dict[str, str]
) -> str | None:
    if card.state != "draft" and card.state != "contest":
        return None

    # T1 has no contest. An open PR does not move it; a merge commits it.
    if card.tier == "T1":
        return "commit" if merged and card.state == "draft" else None

    if not merged:
        return "contest" if card.state == "draft" else None

    if card.state == "contest" and decider_approved(card, approvers, deciders):
        return "commit"
    return None
```

Create `contract/deciders.yml`:

```yaml
# GitHub handle -> the exact `decider` string used on cards.
# A handle absent from this file can never satisfy the Named Decider clause.
# priya-r: "Priya Raman <priya@client.example>"
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_gh.py -v`
Expected: PASS — 13 passed

- [ ] **Step 5: Add the `sync-pr` subcommand to `delivery_os/cli.py`**

Add the import at the top:

```python
from delivery_os.gh import card_ids_in_paths, load_deciders, transition_for
```

Register the subcommand alongside the others in `main`:

```python
    p_sync = sub.add_parser("sync-pr")
    p_sync.add_argument("--changed", required=True, help="newline- or comma-separated paths")
    p_sync.add_argument("--approvers", default="", help="comma-separated GitHub handles")
    p_sync.add_argument("--merged", action="store_true")
    p_sync.add_argument("--deciders", default="contract/deciders.yml")
```

Handle it after the `move` branch:

```python
    if args.cmd == "sync-pr":
        changed = [p for p in re.split(r"[,\n]", args.changed) if p.strip()]
        approvers = [a.strip() for a in args.approvers.split(",") if a.strip()]
        deciders = load_deciders(args.deciders)
        wanted = card_ids_in_paths(changed)
        by_id = {c.id: c for c in cards}
        for card_id in wanted:
            card = by_id.get(card_id)
            if card is None:
                continue
            target = transition_for(card, args.merged, approvers, deciders)
            if target is None:
                print(f"{card_id}  no transition")
                continue
            moved = move_card(card, target, by="github", now=datetime.now(timezone.utc))
            _rewrite(moved)
            print(f"{card_id} -> {target}")
        return 0
```

- [ ] **Step 6: Verify the subcommand end to end**

```bash
cd /Users/akp/Downloads/delivery-os
.venv/bin/python -m delivery_os.cli --root cards new acme "webhook subsystem" --tier T2
printf -- 'priya-r: "Priya Raman <priya@client.example>"\n' > contract/deciders.yml
# fill in decider/eval/value_line/kill_criterion/observation_date on the new card, then:
.venv/bin/python -m delivery_os.cli --root cards sync-pr --changed cards/acme/C-0001-webhook-subsystem.md
# expected: C-0001 -> contest
.venv/bin/python -m delivery_os.cli --root cards sync-pr --changed cards/acme/C-0001-webhook-subsystem.md --merged --approvers sam-k
# expected: C-0001  no transition        (Sam is not the named Decider)
.venv/bin/python -m delivery_os.cli --root cards sync-pr --changed cards/acme/C-0001-webhook-subsystem.md --merged --approvers priya-r
# expected: C-0001 -> commit
```

- [ ] **Step 7: Add the workflow**

Create `.github/workflows/card-sync.yml`:

```yaml
name: card-sync
on:
  pull_request:
    types: [opened, synchronize, reopened, closed]

permissions:
  contents: write
  pull-requests: read

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.ref }}
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e .

      - name: Collect changed card paths
        id: changed
        run: |
          git fetch origin ${{ github.event.pull_request.head.sha }} --depth=1
          git diff --name-only origin/${{ github.event.pull_request.base.ref }}...${{ github.event.pull_request.head.sha }} > changed.txt
          echo "count=$(wc -l < changed.txt)" >> "$GITHUB_OUTPUT"

      - name: Collect approving reviewers
        id: approvers
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh api "repos/${{ github.repository }}/pulls/${{ github.event.pull_request.number }}/reviews" \
            --jq '[.[] | select(.state=="APPROVED") | .user.login] | unique | join(",")' > approvers.txt
          echo "list=$(cat approvers.txt)" >> "$GITHUB_OUTPUT"

      - name: Advance cards
        run: |
          python -m delivery_os.cli --root cards sync-pr \
            --changed "$(cat changed.txt)" \
            --approvers "${{ steps.approvers.outputs.list }}" \
            ${{ github.event.pull_request.merged && '--merged' || '' }}

      - name: Commit state changes
        if: github.event.pull_request.merged
        run: |
          git config user.name "card-sync"
          git config user.email "card-sync@users.noreply.github.com"
          git add cards/
          git diff --staged --quiet || git commit -m "chore: advance card states from PR #${{ github.event.pull_request.number }}"
          git push
```

- [ ] **Step 8: Run the whole suite**

Run: `.venv/bin/pytest -v`
Expected: PASS — 66 passed

- [ ] **Step 9: Commit**

```bash
git add delivery_os/gh.py delivery_os/cli.py tests/test_gh.py contract/deciders.yml .github/workflows/card-sync.yml
git commit -m "feat: PR-merge automation with named-Decider approval gate"
```


---

## Self-review

**Spec coverage.**

| Spec section | Implemented by |
|---|---|
| §3 card fields | Task 1 (`Card`), Task 2 (required-by-tier) |
| §3 Rule 1 — no eval, no spec | Task 2 (`missing-field` on `eval`) |
| §3 Rule 2 — T1 three fields, inherit | Task 2 (`T1_REQUIRED`), Task 7 (`card-t1.md`) |
| §3 orphan rule | Task 3 (`orphan` trigger), Task 7 (`new_card` forces T2) |
| §4 six-state loop | Task 4 (`LEGAL_TRANSITIONS`) |
| §4 tier test and five triggers | Task 3 (`T2_TRIGGERS`) |
| §4 red-eval fork | Task 4 (`verify -> build` and `verify -> contest`) |
| §4 close at Observe | Task 6 (`unrecorded` chases overdue observations) |
| §5 M1 / M2 / M3 | Task 5 |
| §5 scoreboard kept separate | Task 6 (separate function, separate section in report) |
| §5 never-red guard | Task 5 (`never_red`), Task 8 Step 3 |
| §5 nothing per-person | Global Constraints; no task adds one |
| §6 reciprocal SLA, Decider clause | Task 9 |
| §6 native exit | Task 9 (`handover-card.md`) |
| §7 conformance is an eval, not a portal | Task 8 |
| §4 T1 has no contest (fast lane) | Task 4 (`move_card` T1 fast path), Task 10 (`transition_for`) |
| §6 Named Decider clause made enforceable | Task 10 (`decider_approved` gates commit) |
| §9 U2 N and M unset | Task 9 Step 2, provisional values stated |
| §9 U3 Decider clause acceptance | Task 9 Step 4, escalation path defined |

**Gap accepted deliberately:** §9 U1 (spec owners per engagement), U4 (whether T1/T2 sorts cleanly), and U5 (whether behaviour delta reaches zero) are empirical and resolved by running the OS, not by building anything. No task is added for them; M3 and the fifty-card review supply the data.

**Placeholder scan.** No TBD, TODO, "handle edge cases", or "similar to Task N". Every code step contains runnable code. Task 9 is the sole task without an automated test and says so in its heading.

**Type consistency.** `Card` field names are identical across Tasks 1–7. `lint_card` returns `list[Finding]` throughout. `move_card` and `record_verify` both take `(card, ..., by, now)` and return `Card`. `compute_m1` is the only meter taking `now`; `compute_scoreboard` is the only one taking `today`. `state_index` is defined once in `card.py` and used only by `compute_m2`.
