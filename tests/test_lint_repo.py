from pathlib import Path

from delivery_os.card import load_all
from delivery_os.lint import lint_card, lint_corpus

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_CARDS = REPO_ROOT / "cards"


def test_the_repo_corpus_is_not_empty():
    # I10: cards/ used to be an empty (therefore untracked) directory, so on
    # a fresh clone rglob yielded nothing and this whole file passed on zero
    # cards. A guard with nothing to guard is not a guard.
    cards = load_all(REPO_CARDS)
    assert cards, f"no cards under {REPO_CARDS}: the repo-wide lint guard is vacuous"


def test_every_card_in_the_repo_is_valid():
    cards = load_all(REPO_CARDS)
    findings = [f for c in cards for f in lint_card(c)] + lint_corpus(cards, REPO_ROOT)
    assert findings == [], "\n".join(
        f"{f.card_id} {f.rule}: {f.message}" for f in findings)
