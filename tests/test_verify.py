"""C1: 'the eval could not run' is not 'the eval went red'.

pytest exit codes are not binary. Recording exit 5 (no tests collected) as
`verify: fail` writes a permanent red into card history and thereby
satisfies spec 5's never-red guard -- eval theatre defeated by eval theatre.
"""
from pathlib import Path

from delivery_os.card import load_card
from delivery_os.cli import main, verify_card

CARD = """---
id: C-0001
title: t
tier: T1
state: verify
parent: C-0000
eval: {eval}
history: []
---
Something is true.
"""


def _corpus(tmp_path: Path, eval_id: str) -> Path:
    cards = tmp_path / "cards" / "acme"
    cards.mkdir(parents=True)
    (cards / "C-0001-t.md").write_text(CARD.format(eval=eval_id), encoding="utf-8")
    return tmp_path / "cards"


def _eval_file(tmp_path: Path, name: str, body: str) -> None:
    evals = tmp_path / "evals"
    evals.mkdir(exist_ok=True)
    (evals / name).write_text(body, encoding="utf-8")


# --- verify_card: the three outcomes ---------------------------------------

def test_green_eval_is_pass(tmp_path):
    _eval_file(tmp_path, "test_ok.py", "def test_ok():\n    assert True\n")
    card = load_card(_corpus(tmp_path, "evals/test_ok.py::test_ok") / "acme" / "C-0001-t.md")
    outcome, _out, _err = verify_card(card, repo_root=tmp_path)
    assert outcome == "pass"


def test_red_eval_is_fail(tmp_path):
    _eval_file(tmp_path, "test_bad.py", "def test_bad():\n    assert False\n")
    card = load_card(_corpus(tmp_path, "evals/test_bad.py::test_bad") / "acme" / "C-0001-t.md")
    outcome, _out, _err = verify_card(card, repo_root=tmp_path)
    assert outcome == "fail"


def test_missing_eval_file_is_error_not_fail(tmp_path):
    # pytest exits 4 (usage error) here. The old code called that "fail".
    card = load_card(_corpus(tmp_path, "evals/does_not_exist.py::test_x") / "acme" / "C-0001-t.md")
    outcome, _out, err = verify_card(card, repo_root=tmp_path)
    assert outcome == "error"
    assert "could not run" in err


def test_eval_that_collects_nothing_is_error_not_fail(tmp_path):
    # pytest exits 5 (no tests collected).
    _eval_file(tmp_path, "test_empty.py", "# no tests here\n")
    card = load_card(_corpus(tmp_path, "evals/test_empty.py") / "acme" / "C-0001-t.md")
    outcome, _out, err = verify_card(card, repo_root=tmp_path)
    assert outcome == "error"
    assert "could not run" in err


def test_card_with_no_eval_is_error_not_fail(tmp_path):
    card = load_card(_corpus(tmp_path, "null") / "acme" / "C-0001-t.md")
    outcome, _out, err = verify_card(card, repo_root=tmp_path)
    assert outcome == "error"
    assert "no eval" in err


def test_error_surfaces_stderr_not_just_stdout(tmp_path):
    card = load_card(_corpus(tmp_path, "evals/does_not_exist.py::test_x") / "acme" / "C-0001-t.md")
    _outcome, _out, err = verify_card(card, repo_root=tmp_path)
    assert err.strip(), "stderr must be surfaced, not discarded"


# --- main(): what reaches card history -------------------------------------

def _history(root: Path) -> list[dict]:
    return load_card(root / "acme" / "C-0001-t.md").history


def test_unrunnable_eval_writes_nothing_to_history_and_exits_nonzero(tmp_path, monkeypatch):
    root = _corpus(tmp_path, "evals/does_not_exist.py::test_x")
    monkeypatch.chdir(tmp_path)
    code = main(["--root", str(root), "verify", "C-0001"])
    assert code != 0
    assert _history(root) == [], (
        "an eval that could not run must not be recorded as red: doing so "
        "satisfies the spec 5 never-red guard with pure theatre"
    )


def test_genuine_red_is_recorded_as_fail(tmp_path, monkeypatch):
    _eval_file(tmp_path, "test_bad.py", "def test_bad():\n    assert False\n")
    root = _corpus(tmp_path, "evals/test_bad.py::test_bad")
    monkeypatch.chdir(tmp_path)
    assert main(["--root", str(root), "verify", "C-0001"]) == 1
    assert _history(root)[-1]["verify"] == "fail"


def test_genuine_green_is_recorded_as_pass(tmp_path, monkeypatch):
    _eval_file(tmp_path, "test_ok.py", "def test_ok():\n    assert True\n")
    root = _corpus(tmp_path, "evals/test_ok.py::test_ok")
    monkeypatch.chdir(tmp_path)
    assert main(["--root", str(root), "verify", "C-0001"]) == 0
    assert _history(root)[-1]["verify"] == "pass"


def test_verify_on_an_unknown_card_id_is_a_clean_error(tmp_path, monkeypatch):
    root = _corpus(tmp_path, "evals/test_ok.py::test_ok")
    monkeypatch.chdir(tmp_path)
    assert main(["--root", str(root), "verify", "C-9999"]) == 2
