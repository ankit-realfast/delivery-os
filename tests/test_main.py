"""I4: main() and the card writer had zero test coverage.

_rewrite was the only function that overwrites card files, and nothing
drove the CLI entry point at all.
"""
import re
from pathlib import Path

import pytest

from delivery_os.card import Card, dump_card, load_card
from delivery_os.cli import main


def _keys(path: Path) -> list[str]:
    front = path.read_text(encoding="utf-8").split("---\n")[1]
    return re.findall(r"(?m)^([a-z_]+):", front)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --- main(): every subcommand ----------------------------------------------

def test_main_new_writes_a_card_and_exits_zero(repo, capsys):
    assert main(["--root", "cards", "new", "acme", "webhook subsystem"]) == 0
    path = Path(capsys.readouterr().out.strip())
    assert path.exists()
    assert load_card(path).tier == "T2"      # no parent -> T2 by definition


def test_main_lint_is_clean_on_a_freshly_created_card(repo):
    main(["--root", "cards", "new", "acme", "webhook subsystem"])
    assert main(["--root", "cards", "lint"]) == 0


def test_main_lint_exits_nonzero_and_prints_findings(repo, capsys):
    cards = repo / "cards"
    cards.mkdir()
    (cards / "C-0001.md").write_text(
        "---\nid: C-0001\ntitle: t\ntier: T1\nstate: commit\nparent: C-0000\n---\nBody.\n",
        encoding="utf-8")
    assert main(["--root", "cards", "lint"]) == 1
    assert "missing-field" in capsys.readouterr().out


def test_main_report_prints_all_four_numbers(repo, capsys):
    main(["--root", "cards", "new", "acme", "webhook subsystem"])
    assert main(["--root", "cards", "report"]) == 0
    out = capsys.readouterr().out
    for label in ("M1 decision latency", "M2 eval fallibility",
                  "M3 behaviour-delta debt", "SCOREBOARD"):
        assert label in out


def test_main_move_advances_the_card_on_disk(repo, capsys):
    main(["--root", "cards", "new", "acme", "webhook subsystem"])
    capsys.readouterr()
    assert main(["--root", "cards", "move", "C-0001", "contest", "--by", "akp"]) == 0
    assert load_card(next((repo / "cards").rglob("*.md"))).state == "contest"


def test_main_move_on_an_unknown_card_is_a_clean_error(repo, capsys):
    main(["--root", "cards", "new", "acme", "thing"])
    assert main(["--root", "cards", "move", "C-9999", "contest", "--by", "akp"]) == 2
    assert "no card with id C-9999" in capsys.readouterr().err


def test_main_move_on_an_illegal_transition_is_a_clean_error(repo, capsys):
    # Deferred #7: IllegalTransition was uncaught in main(), so card-sync
    # failed the job with a raw traceback and no diagnosis.
    main(["--root", "cards", "new", "acme", "webhook subsystem"])
    assert main(["--root", "cards", "move", "C-0001", "observe", "--by", "akp"]) == 2
    err = capsys.readouterr().err
    assert "illegal transition" in err
    assert "draft -> observe" in err


def test_main_new_refuses_an_unknown_tier(repo):
    with pytest.raises(SystemExit):
        main(["--root", "cards", "new", "acme", "thing", "--tier", "T3"])


# --- I5: the writer must not inflate a T1 card ------------------------------

def test_a_t1_card_survives_a_transition_without_inflating(repo, capsys):
    # Spec 8: "T1 cards carrying more than three fields" is named as the
    # most likely way this OS dies. The old _rewrite wrote every dataclass
    # field, turning the template's 8 keys into 18 on first transition.
    main(["--root", "cards", "new", "acme", "retry webhooks", "--parent", "C-0000"])
    path = Path(capsys.readouterr().out.strip())
    before = _keys(path)
    main(["--root", "cards", "move", "C-0001", "contest", "--by", "akp"])
    after = _keys(path)
    assert after == before, f"transition inflated the card: {sorted(set(after) - set(before))}"
    assert "kill_criterion" not in after
    assert "touches_production_data" not in after


def test_dump_omits_fields_still_at_their_default():
    card = Card(id="C-0001", title="t", tier="T1", state="draft", parent="C-0000",
                eval="evals/x.py::test_x", intent="x")
    keys = re.findall(r"(?m)^([a-z_]+):", dump_card(card))
    assert keys == ["id", "title", "tier", "state", "parent", "eval"]


def test_dump_keeps_a_field_the_author_deliberately_wrote_as_null(repo):
    # `eval: null` and `blocked_on: null` are the T1 template's placeholders;
    # a transition must not silently delete the form the operator fills in.
    path = repo / "C-0001.md"
    path.write_text(
        "---\nid: C-0001\ntitle: t\ntier: T1\nstate: draft\nparent: C-0000\n"
        "eval: null\nblocked_on: null\n---\nBody.\n", encoding="utf-8")
    keys = re.findall(r"(?m)^([a-z_]+):", dump_card(load_card(path)))
    assert keys == ["id", "title", "tier", "state", "parent", "eval", "blocked_on"]


def test_dump_never_writes_loader_owned_fields(repo):
    path = repo / "C-0001.md"
    path.write_text("---\nid: C-0001\ntitle: t\ntier: T1\nstate: draft\n"
                    "parent: C-0000\n---\nBody text.\n", encoding="utf-8")
    out = dump_card(load_card(path))
    assert "path:" not in out
    assert "intent:" not in out
    assert "authored_keys:" not in out
    assert out.endswith("Body text.\n")


def test_dump_round_trips_through_the_loader(repo):
    path = repo / "C-0001.md"
    path.write_text(
        "---\nid: C-0001\ntitle: webhook delivery\ntier: T2\nstate: commit\n"
        "parent: null\ndecider: Priya Raman\neval: evals/x.py::test_x\n"
        'value_line: "tickets: 40/mo -> 5/mo"\nkill_criterion: k\n'
        "observation_date: 2026-09-30\ntouches_production_data: true\n"
        'history:\n  - {state: contest, at: "2026-08-01T09:00:00+00:00", by: akp}\n'
        "---\nEvents reach the endpoint.\n", encoding="utf-8")
    original = load_card(path)
    path.write_text(dump_card(original), encoding="utf-8")
    reloaded = load_card(path)
    for f in ("id", "title", "tier", "state", "decider", "eval", "value_line",
              "kill_criterion", "observation_date", "touches_production_data",
              "history", "intent"):
        assert getattr(reloaded, f) == getattr(original, f), f
