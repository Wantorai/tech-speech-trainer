"""Catalog, navigation, audio, and exercise-isolation checks."""

import wave
from html import unescape
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.exercises import EXERCISES, get_next_exercise
from app.main import APP_DIR, app


@pytest.fixture
def client():
    """Provide an HTTP client for catalog and exercise requests."""
    with TestClient(app) as client:
        yield client


def test_catalog_exposes_metadata_without_transcripts(client):
    """List all exercises without revealing the listening answers or translations."""
    response = client.get("/exercises")
    assert response.status_code == 200
    for exercise in EXERCISES:
        assert f"/exercises/{exercise.id}" in response.text
        assert exercise.title in response.text
        assert exercise.transcript not in unescape(response.text)
        assert exercise.translation_ru not in response.text
    assert 'href="http://testserver/exercises"' in client.get("/").text


def test_catalog_filters_accept_empty_values_and_combine_topic_with_level(client):
    """Support normal form submission and intersection of topic and level filters."""
    assert client.get("/exercises?topic=&level=").status_code == 200
    topic = EXERCISES[-1].topic
    response = client.get("/exercises", params={"topic": topic, "level": 2})
    for exercise in EXERCISES:
        assert (f"/exercises/{exercise.id}" in response.text) == (
            exercise.topic == topic and exercise.level == 2
        )
    assert "упражнений пока нет" in client.get("/exercises?level=4").text
    assert "упражнений пока нет" in client.get("/exercises?topic=unknown").text
    assert client.get("/exercises?level=abc").status_code == 422


@pytest.mark.parametrize(
    "exercise", EXERCISES, ids=[exercise.id for exercise in EXERCISES]
)
def test_each_exercise_has_its_own_answer_translation_and_audio(client, exercise):
    """Check each exercise against its own reference and hide answers on a fresh visit."""
    url = f"/exercises/{exercise.id}"
    page = client.get(url)
    assert page.status_code == 200
    assert exercise.transcript not in unescape(page.text)
    assert exercise.translation_ru not in page.text
    assert exercise.audio_file in page.text
    result = client.post(url, data={"answer": exercise.transcript})
    assert "100%" in result.text
    assert exercise.transcript in unescape(result.text)
    assert exercise.translation_ru in result.text
    other = next(item for item in EXERCISES if item.id != exercise.id)
    assert "100%" not in client.post(url, data={"answer": other.transcript}).text
    with wave.open(str(APP_DIR / "static" / exercise.audio_file), "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getframerate() == 22050
        assert 2 < audio.getnframes() / audio.getframerate() < 30
        assert any(audio.readframes(audio.getnframes()))
    audio_response = client.get(
        "/static/" + exercise.audio_file, headers={"Range": "bytes=0-43"}
    )
    assert audio_response.status_code == 206
    assert audio_response.content[:4] == b"RIFF"


def test_navigation_stops_at_catalog_end_without_claiming_saved_progress(client):
    """Offer the next catalog item after an answer and finish at the catalog link."""
    for index, exercise in enumerate(EXERCISES):
        response = client.post(
            f"/exercises/{exercise.id}", data={"answer": "something"}
        )
        if index < len(EXERCISES) - 1:
            following = EXERCISES[index + 1]
            assert get_next_exercise(exercise.id) == following
            assert f"/exercises/{following.id}" in response.text
            assert "Следующее упражнение" in response.text
        else:
            assert get_next_exercise(exercise.id) is None
            assert "Это последнее упражнение" in response.text
            assert "Следующее упражнение" not in response.text
    assert get_next_exercise("unknown") is None


@pytest.mark.parametrize(
    "exercise", EXERCISES, ids=[exercise.id for exercise in EXERCISES]
)
def test_tutor_context_uses_selected_exercise(client, exercise):
    """Prevent AI feedback for a selected item from using the first exercise text."""
    with patch("app.tutor.request_tutor", side_effect=TimeoutError()) as request:
        response = client.post(
            f"/exercises/{exercise.id}/ai", data={"answer": exercise.transcript}
        )
    assert response.json()["status"] == "timeout"
    data = request.call_args.args[0]
    assert data["transcript"] == exercise.transcript
    assert data["translation_ru"] == exercise.translation_ru
    assert data["exercise_level"] == exercise.level


def test_catalog_ids_audio_and_level_lengths_are_consistent():
    """Keep starter records unique and within the promised level lengths."""
    assert len({exercise.id for exercise in EXERCISES}) == len(EXERCISES)
    assert len({exercise.audio_file for exercise in EXERCISES}) == len(EXERCISES)
    for exercise in EXERCISES:
        count = len(exercise.transcript.split())
        low, high = {1: (10, 15), 2: (20, 30)}[exercise.level]
        assert low <= count <= high
        assert sum(exercise.transcript.count(mark) for mark in ".!?") == exercise.level
