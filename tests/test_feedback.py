"""Checks for deterministic feedback and optional Ollama failure handling."""

import json
from unittest.mock import patch
from urllib.error import URLError

import pytest

from app.feedback import build_feedback, parse_notes, request_notes


def response_for(notes):
    """Wrap vocabulary notes in a completed Ollama response."""
    return {
        "done": True,
        "done_reason": "stop",
        "message": {"content": json.dumps({"notes": notes})},
    }


@pytest.mark.parametrize(
    "reference,answer,expected",
    [
        ("We do not deploy.", "We do deploy.", "В оригинале здесь есть отрицание not"),
        (
            "We do deploy.",
            "We do not deploy.",
            "В ответе здесь появилось отрицание not",
        ),
        (
            "We do not deploy.",
            "We do now deploy.",
            "В оригинале здесь есть отрицание not",
        ),
    ],
)
def test_negation_is_explained_without_inference(reference, answer, expected):
    """Explain missing, added, and replaced negation using deterministic text."""
    with patch("app.feedback.request_notes") as request:
        result = build_feedback(reference, answer, use_ai=True)
    request.assert_not_called()
    assert expected in result.explanations[0]
    assert result.ai_status == "not_needed"


@pytest.mark.parametrize("answer", ["", "...", "x" * 2001])
def test_invalid_answers_are_rejected_before_network_access(answer):
    """Reject invalid learner input before comparison or model requests."""
    with patch("app.feedback.request_notes") as request, pytest.raises(ValueError):
        build_feedback("We deploy.", answer, use_ai=True)
    request.assert_not_called()


def test_ai_is_opt_in_and_correct_answers_skip_it():
    """Avoid model requests by default and for normalized correct answers."""
    with patch("app.feedback.request_notes") as request:
        assert build_feedback("We deploy.", "We.").ai_status == "not_requested"
        result = build_feedback("We don't deploy.", "we do not deploy", use_ai=True)
    request.assert_not_called()
    assert result.comparison.score == 100
    assert result.ai_status == "not_needed"


def test_spelling_hint_keeps_uncertainty_and_score():
    """Keep a spelling hint tentative without forgiving the word replacement."""
    result = build_feedback("The deployment works.", "The deploymnet works.")
    assert "Возможно" in result.explanations[0]
    assert result.comparison.errors == 1


@pytest.mark.parametrize(
    "error,status",
    [
        (TimeoutError(), "timeout"),
        (URLError(TimeoutError()), "timeout"),
        (URLError("connection refused"), "unavailable"),
        (OSError("connection reset"), "unavailable"),
        (ValueError("bad JSON"), "invalid_response"),
    ],
)
def test_provider_failure_preserves_comparison_without_retry(error, status):
    """Keep scores and deterministic explanations when the provider fails."""
    baseline = build_feedback("We write tests.", "We write.")
    with patch("app.feedback.request_notes", side_effect=error) as request:
        result = build_feedback("We write tests.", "We write.", use_ai=True)
    request.assert_called_once()
    assert result.ai_status == status
    assert result.comparison == baseline.comparison
    assert result.explanations == baseline.explanations
    assert result.vocabulary == ()


def test_vocabulary_is_limited_and_kept_separate_from_corrections():
    """Limit inference to three unique reference words without changing the score."""
    notes = [
        {"word": word, "meaning_ru": "Перевод слова."}
        for word in ("write", "tests", "and")
    ]
    with patch(
        "app.feedback.request_notes", return_value=response_for(notes)
    ) as request:
        result = build_feedback("We write tests and review code.", "We.", use_ai=True)
    assert request.call_args.args[1] == ("write", "tests", "and")
    assert result.comparison.errors == 5
    assert len(result.explanations) == 5
    assert len(result.vocabulary) == 3
    assert result.ai_status == "ready"


@pytest.mark.parametrize(
    "notes",
    [
        [],
        [{"word": "other", "meaning_ru": "Перевод."}],
        [{"word": "tests", "meaning_ru": "English only"}],
        [{"word": "tests", "meaning_ru": "я" * 601}],
        [{"word": "tests", "meaning_ru": "Тесты.", "score": 100}],
    ],
)
def test_invalid_notes_are_not_shown(notes):
    """Discard incomplete, unrelated, oversized, or malformed vocabulary notes."""
    with patch("app.feedback.request_notes", return_value=response_for(notes)):
        result = build_feedback("We write tests.", "We write.", use_ai=True)
    assert result.ai_status == "invalid_response"
    assert not result.vocabulary
    assert result.explanations


def test_duplicate_words_and_truncation_are_rejected():
    """Reject duplicate notes and responses stopped at the generation limit."""
    response = response_for(
        [
            {"word": "tests", "meaning_ru": "Тесты."},
            {"word": "tests", "meaning_ru": "Тесты."},
        ]
    )
    with pytest.raises(ValueError):
        parse_notes(response, ("tests", "code"))
    response["done_reason"] = "length"
    with pytest.raises(ValueError):
        parse_notes(response, ("tests",))


def test_http_payload_contains_reference_words_but_no_learner_answer():
    """Send only trusted reference context and requested words to Ollama."""
    with patch("app.feedback.build_opener") as factory:
        factory.return_value.open.return_value.__enter__.return_value.read.return_value = json.dumps(
            response_for([{"word": "tests", "meaning_ru": "Тесты."}])
        ).encode()
        result = build_feedback(
            "We write tests.", "We write HIDDEN_INPUT.", use_ai=True
        )
    request = factory.return_value.open.call_args.args[0]
    payload = json.loads(request.data)
    data = json.loads(payload["messages"][1]["content"])
    assert set(data) == {"transcript", "words"}
    assert "HIDDEN_INPUT" not in json.dumps(payload)
    assert payload["stream"] is False
    assert factory.return_value.open.call_args.kwargs["timeout"] == 45
    assert result.ai_status == "ready"


def test_oversized_http_response_is_rejected():
    """Bound the provider response before JSON decoding."""
    with patch("app.feedback.build_opener") as factory:
        factory.return_value.open.return_value.__enter__.return_value.read.return_value = (
            b"x" * 65537
        )
        with pytest.raises(ValueError, match="Oversized"):
            request_notes(
                "We test.",
                ("test",),
                base_url="http://localhost:11434",
                model="test",
                timeout=1,
            )
