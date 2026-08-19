from pathlib import Path

from delivery_os.card import load_all
from delivery_os.lint import lint_card

REPO_CARDS = Path(__file__).resolve().parent.parent / "cards"


def test_every_card_in_the_repo_is_valid():
    findings = [f for c in load_all(REPO_CARDS) for f in lint_card(c)]
    assert findings == [], "\n".join(f"{f.card_id} {f.rule}: {f.message}" for f in findings)
