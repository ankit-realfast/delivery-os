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


def test_card_shaped_markdown_outside_cards_dir_is_ignored():
    assert card_ids_in_paths(["docs/C-0007-notes.md"]) == []


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
    assert transition_for(card(state="draft"), event="open", approvers=[], deciders=DECIDERS) == "contest"


def test_merged_pr_with_decider_approval_commits_a_t2_card():
    assert transition_for(card(), event="merged", approvers=["priya-r"], deciders=DECIDERS) == "commit"


def test_merged_pr_without_decider_approval_does_not_commit():
    assert transition_for(card(), event="merged", approvers=["sam-k"], deciders=DECIDERS) is None


def test_t1_card_commits_on_merge_with_no_approval_needed():
    t1 = card(id="C-0008", tier="T1", state="draft", parent="C-0007", decider=None)
    assert transition_for(t1, event="merged", approvers=[], deciders=DECIDERS) == "commit"


def test_t1_card_is_not_dragged_into_contest_by_an_open_pr():
    t1 = card(id="C-0008", tier="T1", state="draft", parent="C-0007", decider=None)
    assert transition_for(t1, event="open", approvers=[], deciders=DECIDERS) is None


def test_card_already_past_commit_is_left_alone():
    assert transition_for(card(state="build"), event="merged", approvers=["priya-r"], deciders=DECIDERS) is None


def test_under_tiered_auth_card_cannot_reach_commit_without_the_decider():
    # C4, the proven routing-around: authored `tier: T1`, derives T2 via the
    # auth trigger, lints with a tier-escalation finding -- and still
    # committed on merge with no approvers and no named Decider.
    # decider_approved never failed open; the caller simply never asked it.
    under_tiered = card(id="C-0009", tier="T1", state="draft", parent="C-0001",
                        touches_auth=True, decider=None)
    assert transition_for(under_tiered, event="merged", approvers=[], deciders=DECIDERS) != "commit"


def test_orphan_card_claiming_t1_cannot_reach_commit_on_merge():
    orphan = card(id="C-0010", tier="T1", state="draft", parent=None, decider=None)
    assert transition_for(orphan, event="merged", approvers=[], deciders=DECIDERS) != "commit"


def test_unflaggable_card_claiming_t1_cannot_reach_commit_on_merge():
    c = card(id="C-0011", tier="T1", state="draft", parent="C-0001",
             flag_off=False, decider=None)
    assert transition_for(c, event="merged", approvers=[], deciders=DECIDERS) != "commit"


def test_genuinely_reversible_t1_card_still_commits_on_merge():
    t1 = card(id="C-0012", tier="T1", state="draft", parent="C-0007", decider=None)
    assert transition_for(t1, event="merged", approvers=[], deciders=DECIDERS) == "commit"


def test_abandoned_pr_does_not_drag_a_draft_into_contest():
    # C5: `closed` fires for merge AND for abandonment. With a merged flag,
    # an abandoned PR looked exactly like an open one, so a throwaway PR
    # touching a card file started an unbounded M1 clock against a named
    # client-side individual for a decision never put to them.
    assert transition_for(card(state="draft"), event="abandoned",
                          approvers=[], deciders=DECIDERS) is None


def test_abandoned_pr_does_not_commit_an_approved_contest_card():
    assert transition_for(card(state="contest"), event="abandoned",
                          approvers=["priya-r"], deciders=DECIDERS) is None


def test_abandoned_pr_does_not_commit_a_t1_draft():
    t1 = card(id="C-0008", tier="T1", state="draft", parent="C-0007", decider=None)
    assert transition_for(t1, event="abandoned", approvers=[], deciders=DECIDERS) is None


def test_abandoned_never_reverses_an_existing_contest():
    # Explicitly NOT contest -> draft. transition_for cannot know which PR
    # moved this card to contest; reversing would let any throwaway PR erase
    # genuine client decision latency from a contractual meter.
    assert transition_for(card(state="contest"), event="abandoned",
                          approvers=[], deciders=DECIDERS) is None


def test_unknown_pr_event_is_refused_not_guessed():
    import pytest
    with pytest.raises(ValueError, match="unknown PR event"):
        transition_for(card(state="draft"), event="closed",
                       approvers=[], deciders=DECIDERS)


def test_merged_pr_contests_a_t2_card_introduced_by_that_same_pr():
    # C3: the card was ADDED on the PR branch, so no earlier event ever saw
    # it and it is still `draft` at merge. Returning None here left it with
    # no contest history ever, permanently invisible to compute_m1.
    assert transition_for(card(state="draft"), event="merged",
                          approvers=[], deciders=DECIDERS) == "contest"


def test_merged_pr_does_not_let_a_t2_draft_skip_contest_even_with_approval():
    # Spec 4: T2 goes draft -> contest -> commit. A zero-length contest
    # recorded by the supplier's own workflow would make M1 read zero.
    assert transition_for(card(state="draft"), event="merged",
                          approvers=["priya-r"], deciders=DECIDERS) == "contest"


def test_merged_pr_commits_a_t1_card_introduced_by_that_same_pr():
    t1 = card(id="C-0008", tier="T1", state="draft", parent="C-0007", decider=None)
    assert transition_for(t1, event="merged", approvers=[], deciders=DECIDERS) == "commit"


# --- I12: the corpus root is threaded through -------------------------------

def test_a_non_default_root_is_honoured():
    # The literal "cards" was hardcoded here while the loader honoured
    # --root, so any non-default root made sync-pr silently match nothing.
    assert card_ids_in_paths(["corpus/acme/C-0007-x.md"], root="corpus") == ["C-0007"]


def test_a_nested_root_is_honoured():
    assert card_ids_in_paths(["a/b/acme/C-0007-x.md"], root="a/b") == ["C-0007"]


def test_the_default_root_still_matches_cards():
    assert card_ids_in_paths(["cards/acme/C-0007-x.md"]) == ["C-0007"]


def test_a_path_outside_the_given_root_is_ignored():
    assert card_ids_in_paths(["cards/acme/C-0007-x.md"], root="corpus") == []


def test_a_root_prefix_must_match_from_the_start_not_anywhere():
    assert card_ids_in_paths(["docs/cards/C-0007-x.md"], root="cards") == []


# --- deferred #9: the id must not swallow a longer number -------------------

def test_a_five_digit_card_number_is_not_read_as_a_four_digit_one():
    # "C-00071-x.md" matched as C-0007 and card-sync wrote state to a
    # DIFFERENT card -- silent state corruption.
    assert card_ids_in_paths(["cards/acme/C-00071-webhooks.md"]) == []


def test_a_four_digit_id_followed_by_a_separator_still_matches():
    assert card_ids_in_paths(["cards/acme/C-0007-webhooks.md"]) == ["C-0007"]
    assert card_ids_in_paths(["cards/acme/C-0007.md"]) == ["C-0007"]
