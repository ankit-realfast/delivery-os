from datetime import date, datetime, timezone
from pathlib import Path

from delivery_os.card import Card, load_card
from delivery_os.cli import new_card, next_card_id, render_report, verify_card
from delivery_os.machine import record_verify

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


def test_verify_card_passes_and_records_pass_in_history(tmp_path):
    evals_dir = tmp_path / "evals"
    evals_dir.mkdir()
    (evals_dir / "test_ok.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    card = Card(
        id="C-0001", title="t", tier="T1", state="verify",
        parent="C-0000", eval="evals/test_ok.py::test_ok",
    )
    passed, output = verify_card(card, root=tmp_path)
    assert passed is True
    updated = record_verify(card, passed=passed, by="ci", now=NOW)
    assert updated.history[-1]["verify"] == "pass"


def test_verify_card_fails_and_records_fail_in_history(tmp_path):
    evals_dir = tmp_path / "evals"
    evals_dir.mkdir()
    (evals_dir / "test_bad.py").write_text(
        "def test_bad():\n    assert False\n", encoding="utf-8"
    )
    card = Card(
        id="C-0002", title="t", tier="T1", state="verify",
        parent="C-0000", eval="evals/test_bad.py::test_bad",
    )
    passed, output = verify_card(card, root=tmp_path)
    assert passed is False
    updated = record_verify(card, passed=passed, by="ci", now=NOW)
    assert updated.history[-1]["verify"] == "fail"
