"""I2/I3: rules a single card cannot see.

A T1 card with `parent: C-9999` and two files sharing id C-0006 both linted
clean and exited 0, and Rule 1 was enforced only as string non-emptiness so
`eval: "make it smarter"` reached commit.
"""
from pathlib import Path

import pytest

from delivery_os.card import load_all
from delivery_os.cli import main
from delivery_os.lint import lint_corpus

T1 = """---
id: {id}
title: t
tier: T1
state: {state}
parent: {parent}
eval: {eval}
---
Something is true.
"""

T2 = """---
id: C-0001
title: parent
tier: T2
state: commit
parent: null
decider: Priya
eval: evals/ok.py::test_x
value_line: v
kill_criterion: k
observation_date: 2026-12-01
---
Parent card.
"""


def _corpus(tmp_path: Path, **files: str) -> Path:
    root = tmp_path / "cards"
    root.mkdir(exist_ok=True)
    for name, body in files.items():
        (root / f"{name}.md").write_text(body, encoding="utf-8")
    (tmp_path / "evals").mkdir(exist_ok=True)
    (tmp_path / "evals" / "ok.py").write_text("def test_x():\n    assert True\n",
                                              encoding="utf-8")
    return root


def _rules(findings) -> set[str]:
    return {f.rule for f in findings}


# --- I2: dangling parents ---------------------------------------------------

def test_a_dangling_parent_is_a_finding(tmp_path):
    root = _corpus(tmp_path, **{"C-0002": T1.format(
        id="C-0002", state="commit", parent="C-9999", eval="evals/ok.py::test_x")})
    findings = lint_corpus(load_all(root), tmp_path)
    assert "dangling-parent" in _rules(findings)
    assert "C-9999" in next(f.message for f in findings if f.rule == "dangling-parent")


def test_a_resolvable_parent_is_clean(tmp_path):
    root = _corpus(tmp_path, **{
        "C-0001": T2,
        "C-0002": T1.format(id="C-0002", state="commit", parent="C-0001",
                            eval="evals/ok.py::test_x")})
    assert lint_corpus(load_all(root), tmp_path) == []


def test_dos_lint_exits_nonzero_on_a_dangling_parent(tmp_path, monkeypatch, capsys):
    _corpus(tmp_path, **{"C-0002": T1.format(
        id="C-0002", state="commit", parent="C-9999", eval="evals/ok.py::test_x")})
    monkeypatch.chdir(tmp_path)
    assert main(["--root", "cards", "lint"]) == 1
    assert "dangling-parent" in capsys.readouterr().out


# --- I2: duplicate ids ------------------------------------------------------

def test_two_files_sharing_an_id_is_a_finding(tmp_path):
    body = T1.format(id="C-0006", state="draft", parent="null", eval="null")
    root = _corpus(tmp_path, **{"C-0006-a": body, "C-0006-b": body})
    findings = lint_corpus(load_all(root), tmp_path)
    assert "duplicate-id" in _rules(findings)
    message = next(f.message for f in findings if f.rule == "duplicate-id")
    assert "C-0006-a.md" in message and "C-0006-b.md" in message


def test_distinct_ids_are_clean(tmp_path):
    root = _corpus(tmp_path, **{
        "C-0006": T1.format(id="C-0006", state="draft", parent="null", eval="null"),
        "C-0007": T1.format(id="C-0007", state="draft", parent="null", eval="null")})
    assert "duplicate-id" not in _rules(lint_corpus(load_all(root), tmp_path))


def test_dos_lint_exits_nonzero_on_duplicate_ids(tmp_path, monkeypatch, capsys):
    body = T1.format(id="C-0006", state="draft", parent="null", eval="null")
    _corpus(tmp_path, **{"C-0006-a": body, "C-0006-b": body})
    monkeypatch.chdir(tmp_path)
    assert main(["--root", "cards", "lint"]) == 1
    assert "duplicate-id" in capsys.readouterr().out


# --- I3: rule 1, the eval must resolve --------------------------------------

def test_a_prose_eval_does_not_resolve(tmp_path):
    # Rule 1: "if you cannot write the eval, you do not have a spec, you have
    # a wish." String non-emptiness let this reach commit.
    root = _corpus(tmp_path, **{"C-0001": T2.replace(
        "eval: evals/ok.py::test_x", 'eval: "make it smarter"')})
    assert "unresolvable-eval" in _rules(lint_corpus(load_all(root), tmp_path))


def test_an_eval_pointing_at_a_missing_file_does_not_resolve(tmp_path):
    root = _corpus(tmp_path, **{"C-0001": T2.replace(
        "evals/ok.py::test_x", "evals/gone.py::test_x")})
    assert "unresolvable-eval" in _rules(lint_corpus(load_all(root), tmp_path))


def test_an_eval_pointing_at_a_real_file_resolves(tmp_path):
    root = _corpus(tmp_path, **{"C-0001": T2})
    assert "unresolvable-eval" not in _rules(lint_corpus(load_all(root), tmp_path))


def test_a_bare_file_path_with_no_node_id_resolves(tmp_path):
    root = _corpus(tmp_path, **{"C-0001": T2.replace(
        "evals/ok.py::test_x", "evals/ok.py")})
    assert "unresolvable-eval" not in _rules(lint_corpus(load_all(root), tmp_path))


def test_a_draft_card_is_not_yet_asked_to_resolve_its_eval(tmp_path):
    # The rule is "must not LEAVE contest"; drafting stays cheap (I6).
    root = _corpus(tmp_path, **{"C-0002": T1.format(
        id="C-0002", state="draft", parent="null", eval='"make it smarter"')})
    assert "unresolvable-eval" not in _rules(lint_corpus(load_all(root), tmp_path))


def test_dos_lint_exits_nonzero_on_a_wish(tmp_path, monkeypatch, capsys):
    _corpus(tmp_path, **{"C-0001": T2.replace(
        "eval: evals/ok.py::test_x", 'eval: "make it smarter"')})
    monkeypatch.chdir(tmp_path)
    assert main(["--root", "cards", "lint"]) == 1
    assert "unresolvable-eval" in capsys.readouterr().out
