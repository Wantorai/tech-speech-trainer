"""Validate generated drafts independently from model availability."""

import json
from unittest.mock import patch

import pytest

from app.exercises import EXERCISES, TOPIC_ORDER
from app.generation import prepare_generation, request_draft, validate_draft


def response(text, translation="Я исправляю ошибки и обсуждаю изменения с коллегами."):
    """Wrap draft fields in a complete Ollama response."""
    return {
        "done": True,
        "done_reason": "stop",
        "message": {
            "content": json.dumps({"transcript": text, "translation_ru": translation})
        },
    }


def test_valid_draft_and_repeat_detection():
    """Accept a bounded English draft and reject it when already generated."""
    text = "I fix application bugs and discuss the changes with my colleagues."
    assert validate_draft(response(text), 1)["transcript"] == text
    with pytest.raises(ValueError, match="Duplicate"):
        validate_draft(response(text.upper()), 1, (text,))


@pytest.mark.parametrize(
    "text",
    [
        "I work.",
        " ".join(["word"] * 16) + ".",
        "Я работаю в команде и каждый день исправляю ошибки в приложении.",
        "I fix application bugs and discuss the changes with my colleagues",
    ],
)
def test_rejects_invalid_language_length_or_sentence(text):
    """Reject drafts that fail measurable language and level constraints."""
    with pytest.raises(ValueError):
        validate_draft(response(text), 1)


def test_rejects_catalog_duplicates_and_missing_translation():
    """Keep prepared references out of new drafts and require Russian text."""
    with pytest.raises(ValueError, match="Duplicate"):
        validate_draft(response(EXERCISES[0].transcript), 1)
    with pytest.raises(ValueError, match="Russian"):
        validate_draft(
            response(
                "I fix application bugs and discuss the changes with my colleagues.",
                "English only",
            ),
            1,
        )


@pytest.mark.parametrize(
    "value", [None, {}, {"done": False}, {"done": True, "done_reason": "length"}]
)
def test_rejects_incomplete_responses(value):
    """Reject truncated model envelopes before accepting any draft content."""
    with pytest.raises(ValueError):
        validate_draft(value, 1)


def test_preparation_and_provider_settings():
    """Send a reproducible situation and generation options without changing tutor defaults."""
    data = prepare_generation(TOPIC_ORDER[0], 4, 42)
    assert data == prepare_generation(TOPIC_ORDER[0], 4, 42)
    assert data["word_range"] == [60, 85]
    with patch("app.generation.request_tutor") as request:
        request_draft(data, 42)
    assert request.call_args.kwargs["options"]["temperature"] == 0.7
    assert request.call_args.kwargs["options"]["seed"] == 42
    with pytest.raises(ValueError):
        prepare_generation("unknown", 1, 42)


@pytest.mark.parametrize("level", [2, 3, 4])
def test_longer_levels_follow_their_own_constraints(level):
    """Accept long drafts with valid structure and reject a lost level-four question."""
    text = next(item.transcript for item in EXERCISES if item.level == level)
    text = text[:-1] + " today."
    assert validate_draft(response(text), level)["transcript"] == text
    if level == 4:
        with pytest.raises(ValueError, match="interviewer"):
            validate_draft(response(text.replace("?", ".")), level)


def test_cli_records_provider_failure_without_creating_exercise(tmp_path, monkeypatch):
    """Persist a failed request for inspection without silently retrying the model."""
    from scripts import generate_exercise

    monkeypatch.setattr(generate_exercise, "ROOT", tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["generate_exercise", "--topic", "1", "--level", "1", "--seed", "42"],
    )
    with patch.object(
        generate_exercise, "request_draft", side_effect=TimeoutError("timeout")
    ) as request:
        assert generate_exercise.main() == 1
        assert request.call_count == 1
    records = list((tmp_path / "var" / "generated-drafts").glob("*.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_text(encoding="utf-8"))
    assert record["status"] == "rejected"
    assert record["seed"] == 42
    assert "draft" not in record
