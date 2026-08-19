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
