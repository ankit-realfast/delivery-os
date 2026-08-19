from datetime import date, datetime, timezone
from pathlib import Path

from delivery_os.card import Card, load_card
from delivery_os.cli import new_card, next_card_id, render_report, verify_card
from delivery_os.meters import compute_m1
from delivery_os.machine import record_verify

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


def test_next_card_id_starts_at_one(tmp_path):
    assert next_card_id(tmp_path) == "C-0001"


def test_next_card_id_increments_past_the_highest(tmp_path):
    new_card(tmp_path, "acme", "first thing", tier="T2", parent=None)
    new_card(tmp_path, "acme", "second thing", tier="T1", parent="C-0001")
    assert next_card_id(tmp_path) == "C-0003"


def test_next_card_id_uses_highest_id_not_file_count(tmp_path):
    # A naive len(ids) + 1 count would give the same answer as max(ids) + 1
    # while ids are contiguous, so it can't be told apart from that test
    # above. Delete the middle card to open a gap: a count-based
    # implementation would now collide with C-0003 (2 files -> "C-0003"),
    # while max(ids) + 1 correctly still returns "C-0004".
    new_card(tmp_path, "acme", "first thing", tier="T2", parent=None)
    second_path = new_card(tmp_path, "acme", "second thing", tier="T1", parent="C-0001")
    new_card(tmp_path, "acme", "third thing", tier="T1", parent="C-0001")
    second_path.unlink()
    assert next_card_id(tmp_path) == "C-0004"


def test_new_t1_card_is_three_authored_fields(tmp_path):
    path = new_card(tmp_path, "acme", "retry webhooks", tier="T1", parent="C-0001")
    card = load_card(path)
    assert card.tier == "T1"
    assert card.parent == "C-0001"
    assert card.state == "draft"
    assert card.eval is None
    assert path.name == "C-0001-retry-webhooks.md"


def test_new_card_title_round_trips_quotes_and_backslashes(tmp_path):
    # The title sits inside a double-quoted YAML scalar, where both '"' and
    # '\' are escape-significant. The assertion that matters is not "it
    # didn't crash" -- it's that the exact original characters come back
    # out of load_card, not some lossy stand-in (e.g. '"' silently turned
    # into "'").
    hostile_title = r'Fix "quick win" bug \ in the parser'
    path = new_card(tmp_path, "acme", hostile_title, tier="T1", parent="C-0001")
    assert load_card(path).title == hostile_title


def test_new_orphan_card_is_written_as_t2(tmp_path):
    path = new_card(tmp_path, "acme", "webhook subsystem", tier="T1", parent=None)
    assert load_card(path).tier == "T2"


def test_report_renders_all_four_numbers(tmp_path):
    new_card(tmp_path, "acme", "webhook subsystem", tier="T2", parent=None)
    cards = [load_card(p) for p in Path(tmp_path).rglob("*.md")]
    out = render_report(cards, now=NOW, today=date(2026, 8, 19))
    assert "M1 decision latency" in out
    assert "M2 eval fallibility" in out
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
    outcome, _out, _err = verify_card(card, repo_root=tmp_path)
    assert outcome == "pass"
    updated = record_verify(card, passed=True, by="ci", now=NOW)
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
    outcome, _out, _err = verify_card(card, repo_root=tmp_path)
    assert outcome == "fail"
    updated = record_verify(card, passed=False, by="ci", now=NOW)
    assert updated.history[-1]["verify"] == "fail"


# --- deferred #9: next_card_id must not read a five-digit name as four ------

def test_next_card_id_ignores_a_five_digit_card_number(tmp_path):
    # A file named C-00071-x.md used to parse as 7, so the next id was
    # C-0008 -- while C-0007 may also exist. Same boundary bug as CARD_RE.
    (tmp_path / "C-00071-x.md").write_text("---\nid: C-00071\n---\nx\n", encoding="utf-8")
    (tmp_path / "C-0003-y.md").write_text("---\nid: C-0003\n---\nx\n", encoding="utf-8")
    assert next_card_id(tmp_path) == "C-0004"


# --- deferred #6 / #8: sane zero-state text and an unassigned label ---------

def test_empty_corpus_reports_words_not_none():
    out = render_report([], now=NOW, today=date(2026, 8, 19))
    assert "None" not in out
    assert "no cards in the corpus" in out
    assert "median n/a" in out
    assert "value lines moved n/a" in out


def test_a_card_with_no_decider_is_labelled_unassigned():
    c = Card(id="C-0001", title="t", tier="T2", state="contest", parent=None,
             eval="evals/x.py::test_x", intent="x", decider=None,
             history=[{"state": "contest", "at": "2026-08-18T12:00:00+00:00", "by": "x"}])
    assert compute_m1([c], now=NOW)["open"][0]["decider"] == "unassigned"
    out = render_report([c], now=NOW, today=date(2026, 8, 19))
    assert "waiting 24.0h on unassigned for C-0001" in out
    assert "None" not in out


def test_open_items_are_ordered_longest_wait_first():
    def waiting(card_id, since):
        return Card(id=card_id, title="t", tier="T2", state="contest", parent=None,
                    decider="Priya", eval="evals/x.py::test_x", intent="x",
                    history=[{"state": "contest", "at": since, "by": "x"}])
    cards = [
        waiting("C-0001", "2026-08-19T06:00:00+00:00"),   # 6h
        waiting("C-0002", "2026-08-17T12:00:00+00:00"),   # 48h
        waiting("C-0003", "2026-08-18T12:00:00+00:00"),   # 24h
    ]
    m1 = compute_m1(cards, now=NOW)
    assert [o["id"] for o in m1["open"]] == ["C-0002", "C-0003", "C-0001"]
    assert [o["hours"] for o in m1["open"]] == [48.0, 24.0, 6.0]
