"""Learning-related regressions for deterministic transcription comparison."""

import pytest

from app.comparison import compare, normalize
from app.exercises import FIRST_EXERCISE


@pytest.mark.parametrize(
    "answer",
    [
        FIRST_EXERCISE.transcript,
        "i WORK as a frontend developer and build applications for small businesses",
        "I work as a frontend developer\n and  build applications for small businesses!",
    ],
)
def test_equivalent_formatting_is_perfect(answer):
    """Ensure formatting differences do not reduce transcription accuracy."""
    result = compare(FIRST_EXERCISE.transcript, answer)
    assert result.score == 100
    assert result.matches == result.reference_count == 12
    assert result.differences == ()


@pytest.mark.parametrize(
    ("reference", "answer"),
    [
        ("We don't deploy on Friday.", "We do not deploy on Friday."),
        ("I’m a developer.", "I am a developer."),
        ("I have three years of experience.", "I have 3 years of experience."),
        ("We cannot release yet.", "We can't release yet."),
    ],
)
def test_supported_equivalent_spellings(reference, answer):
    """Accept supported contractions and number spellings as equivalent."""
    assert compare(reference, answer).score == 100


def test_missing_negation_is_a_missing_word_not_a_typo():
    """Count an omitted negation as a missing word without a spelling hint."""
    result = compare("We do not deploy today.", "We do deploy today.")
    assert result.score == 80
    assert [(item.kind, item.expected, item.heard) for item in result.differences] == [
        ("missing", "not", "")
    ]
    assert not result.differences[0].possible_typo


def test_repetition_is_counted_as_one_extra_word():
    """Penalize a repeated word once while preserving surrounding matches."""
    result = compare("Our team reviews code.", "Our team team reviews code.")
    assert result.matches == 4
    assert result.errors == 1
    assert result.score == 75
    assert [(item.kind, item.heard) for item in result.differences] == [
        ("extra", "team")
    ]


@pytest.mark.parametrize("misspelling", ["deploymnet", "deploymnt", "deployments"])
def test_possible_spelling_error_does_not_change_the_score(misspelling):
    """Keep the full error penalty when a replacement has a spelling hint."""
    result = compare(
        "Check the deployment pipeline.", f"Check the {misspelling} pipeline."
    )
    assert result.score == 75
    assert result.differences[0].kind == "replacement"
    assert result.differences[0].possible_typo


def test_different_technical_word_is_not_tagged_as_typo():
    """Avoid spelling hints for clearly different technical words."""
    difference = compare("Use the database.", "Use the dashboard.").differences[0]
    assert (difference.expected, difference.heard) == ("database", "dashboard")
    assert not difference.possible_typo


def test_apostrophe_is_not_discarded_when_it_changes_words():
    """Preserve apostrophes that distinguish words or ambiguous contractions."""
    assert compare("We'll deploy.", "Well deploy.").errors > 0
    assert normalize("It's ready.") == ["it's", "ready"]  # 's is ambiguous.


def test_many_extra_words_cannot_produce_negative_accuracy():
    """Keep accuracy at zero when extra words exceed the reference length."""
    result = compare("We deploy.", "We deploy one two three four five.")
    assert result.matches == 2
    assert result.errors == 5
    assert result.score == 0


def test_empty_answer_is_all_missing_but_empty_reference_is_invalid():
    """Treat an empty answer as omissions and reject an empty reference."""
    assert compare("We deploy.", "").score == 0
    with pytest.raises(ValueError):
        compare("...", "anything")


@pytest.mark.parametrize(
    ("reference", "answer"),
    [
        ("We did not update the database.", "We did update the dashboard."),
        ("a b c", "c a b"),
        ("one two one", "one one two"),
        ("I work as a frontend developer.", "I am a developer."),
    ],
)
def test_alignment_accounts_for_every_input_word(reference, answer):
    """Ensure alignment preserves every normalized word from both inputs."""
    result = compare(reference, answer)
    assert [item.expected for item in result.alignment if item.expected] == normalize(
        reference
    )
    assert [item.heard for item in result.alignment if item.heard] == normalize(answer)
    assert len(result.differences) == result.errors


def test_missing_word_does_not_shift_all_following_matches():
    """Ensure one omission does not misalign the remaining words."""
    result = compare(
        FIRST_EXERCISE.transcript, FIRST_EXERCISE.transcript.replace("frontend ", "")
    )
    assert result.score == 91.7
    assert result.matches == 11
    assert result.errors == 1


def test_two_independent_errors_are_both_reported():
    """Report an omission and a substitution together in the same answer."""
    result = compare("We did not update the database.", "We did update the dashboard.")
    assert {(item.kind, item.expected, item.heard) for item in result.differences} == {
        ("missing", "not", ""),
        ("replacement", "database", "dashboard"),
    }
