"""Offline checks for explanation evaluation and model output boundaries."""

import json
from unittest.mock import patch

import pytest

from scripts.evaluate_explanations import evaluate_case, validate_explanations


@pytest.mark.parametrize(
    "answer", ["", "...", "  ", "We don't deploy.", "We do not deploy."]
)
def test_empty_and_equivalent_answers_do_not_call_model(answer):
    """Skip inference for empty input and normalized perfect matches."""
    with patch("scripts.evaluate_explanations.api") as api:
        result = evaluate_case(
            {"id": "local", "transcript": "We don't deploy.", "answer": answer},
            "test",
            1,
        )
    api.assert_not_called()
    assert not result["request_sent"]
    assert result["status"] in {"rejected_empty", "skipped_correct"}


@pytest.mark.parametrize("ids", [[1, 1], [1], [1, 3], [True, 2], ["1", 2]])
def test_missing_duplicate_or_invalid_ids_are_rejected(ids):
    """Reject output that cannot map exactly to the supplied differences."""
    feedback = {
        "explanations": [
            {"difference_id": item, "explanation_ru": "Пропущено слово."}
            for item in ids
        ]
    }
    with pytest.raises(ValueError):
        validate_explanations(feedback, [{"id": 1}, {"id": 2}])


@pytest.mark.parametrize(
    "feedback",
    [
        {"explanations": [], "score": 100},
        {"explanations": "wrong"},
        {"explanations": [{"difference_id": 1, "explanation_ru": "English only"}]},
        {"explanations": [{"difference_id": 1, "explanation_ru": "я" * 1201}]},
    ],
)
def test_invalid_feedback_contract_is_rejected(feedback):
    """Reject extra fields, invalid containers, and unsuitable explanation text."""
    with pytest.raises(ValueError):
        validate_explanations(feedback, [{"id": 1}])


def test_request_uses_computed_differences_without_review_labels():
    """Send computed omissions while keeping evaluation notes out of the prompt."""
    feedback = {
        "explanations": [
            {"difference_id": 1, "explanation_ru": "Пропущено not, меняется отрицание."}
        ]
    }
    with patch("scripts.evaluate_explanations.api") as api:
        api.return_value = {
            "done": True,
            "done_reason": "stop",
            "message": {"content": json.dumps(feedback)},
        }
        result = evaluate_case(
            {
                "id": "negation",
                "transcript": "We do not deploy.",
                "answer": "We do deploy.",
                "review_note": "SECRET_LABEL",
                "expected_pairs": [["fake", "label"]],
            },
            "test",
            1,
        )
    payload = api.call_args.args[1]
    data = json.loads(payload["messages"][1]["content"])
    assert data["differences"] == [
        {
            "id": 1,
            "kind": "missing",
            "expected": "not",
            "heard": "",
            "possible_typo": False,
        }
    ]
    assert "SECRET_LABEL" not in json.dumps(payload)
    assert "expected_pairs" not in data
    assert result["status"] == "valid"


@pytest.mark.parametrize(
    "response",
    [
        {"done": True, "done_reason": "length", "message": {"content": "{}"}},
        {"done": True, "done_reason": "stop", "message": {"content": "not JSON"}},
        [],
    ],
)
def test_malformed_or_truncated_responses_are_recorded(response):
    """Keep invalid model responses as evaluation failures instead of accepting them."""
    with patch("scripts.evaluate_explanations.api", return_value=response):
        result = evaluate_case(
            {"id": "missing", "transcript": "We deploy today.", "answer": "We deploy."},
            "test",
            1,
        )
    assert result["status"] == "error"
    assert "elapsed_seconds" in result


def test_timeout_is_not_retried():
    """Record a timeout without issuing another expensive inference request."""
    with patch("scripts.evaluate_explanations.api", side_effect=TimeoutError) as api:
        result = evaluate_case(
            {"id": "missing", "transcript": "We deploy today.", "answer": "We deploy."},
            "test",
            1,
        )
    api.assert_called_once()
    assert result["status"] == "error"


def test_valid_structure_does_not_guarantee_correct_meaning():
    """Document that semantic mistakes still require review beyond validation."""
    validate_explanations(
        {
            "explanations": [
                {
                    "difference_id": 1,
                    "explanation_ru": "В оригинале пропущено слово not.",
                }
            ]
        },
        [{"id": 1, "kind": "missing", "expected": "not", "heard": ""}],
    )
