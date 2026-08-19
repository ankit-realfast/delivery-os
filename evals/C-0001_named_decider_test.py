"""Acceptance eval for C-0001 -- the Named Decider clause is contractual.

Run by `dos verify C-0001`, not by the unit suite (pyproject pins
testpaths = ["tests"]). It tests the card's intent, not the code: the
clause and its Decision Window must actually be in the contract, and the
Decision Window must be measured by M1, or decision latency is
unattributable and the reciprocal SLA cannot be honestly offered.
"""
from pathlib import Path

def _text(path: Path) -> str:
    """File text with line wrapping collapsed.

    Markdown wraps prose, so "Delivery Window" is really "Delivery\nWindow"
    in the source. A raw substring check went red on the wrap and not on the
    clause being absent -- the eval was wrong, not the build. Spec 4's
    red-eval fork: rebuild, free, minutes, nobody is informed.
    """
    return " ".join(path.read_text(encoding="utf-8").split())


REPO = Path(__file__).resolve().parent.parent
CLAUSE = REPO / "contract" / "decider-clause.md"
SCHEDULE_A = REPO / "contract" / "reciprocal-sla.md"


def test_the_clause_exists_and_names_the_named_decider():
    assert CLAUSE.is_file(), f"{CLAUSE} is missing"
    text = _text(CLAUSE)
    assert "Named Decider" in text
    assert "authority to approve scope" in text


def test_the_clause_binds_delay_to_the_decision_window():
    text = _text(CLAUSE)
    assert "Decision Window" in text
    assert "Delivery Window" in text
    assert "suspended" in text, "an unenforced clause does not make M1 contractual"


def test_schedule_a_measures_the_decision_window_by_m1():
    assert SCHEDULE_A.is_file(), f"{SCHEDULE_A} is missing"
    text = _text(SCHEDULE_A)
    assert "Decision Window" in text
    assert "M1" in text, "the Decision Window must be measured by M1, not by opinion"


def test_the_handle_mapping_the_clause_relies_on_exists():
    # decider_approved can only match through this file; without it, no
    # GitHub approval can ever satisfy the Named Decider clause.
    assert (REPO / "contract" / "deciders.yml").is_file()
