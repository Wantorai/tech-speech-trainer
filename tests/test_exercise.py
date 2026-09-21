"""HTTP checks for the first real listening exercise, with no running AI."""

import wave

import pytest
from fastapi.testclient import TestClient

from app.exercises import FIRST_EXERCISE
from app.main import APP_DIR, app

URL = f"/exercises/{FIRST_EXERCISE.id}"


@pytest.fixture
def client():
    """Provide an in-process HTTP client within the application lifespan."""
    with TestClient(app) as client:
        yield client


def test_original_is_not_rendered_before_submission(client):
    """Keep the transcript and translation hidden before a valid submission."""
    response = client.get(URL)
    assert response.status_code == 200
    assert FIRST_EXERCISE.transcript not in response.text
    assert FIRST_EXERCISE.translation_ru not in response.text
    assert "<audio" in response.text and 'name="answer"' in response.text
    assert "result-panel" not in response.text


def test_correct_answer_reveals_original_and_perfect_score(client):
    """Reveal a perfect result after submission and hide it on a fresh visit."""
    response = client.post(URL, data={"answer": FIRST_EXERCISE.transcript})
    assert response.status_code == 200
    assert "100%" in response.text
    assert "Всё совпало!" in response.text
    assert FIRST_EXERCISE.transcript in response.text
    assert FIRST_EXERCISE.translation_ru in response.text
    assert response.headers["cache-control"] == "no-store"
    assert FIRST_EXERCISE.transcript not in client.get(URL).text
    assert FIRST_EXERCISE.translation_ru not in client.get(URL).text


@pytest.mark.parametrize("answer", ["", " \n\t", "...?!", "word " * 401])
def test_invalid_answer_shows_russian_error_without_revealing_original(client, answer):
    """Reject invalid answers with a Russian error and keep the transcript hidden."""
    response = client.post(URL, data={"answer": answer})
    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert FIRST_EXERCISE.transcript not in response.text
    assert FIRST_EXERCISE.translation_ru not in response.text


def test_user_markup_is_escaped_in_the_answer_and_feedback(client):
    """Ensure submitted HTML is displayed as text rather than executable markup."""
    response = client.post(URL, data={"answer": '<script>alert("hello")</script>'})
    assert response.status_code == 200
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text
    assert FIRST_EXERCISE.translation_ru in response.text


def test_unknown_exercise_is_not_silently_replaced(client):
    """Return HTTP 404 for unknown exercise IDs on both GET and POST."""
    assert client.get("/exercises/missing").status_code == 404
    assert (
        client.post("/exercises/missing", data={"answer": "anything"}).status_code
        == 404
    )


def test_audio_is_bundled_and_supports_seeking(client):
    """Check the bundled WAV format and byte range responses used for seeking."""
    audio_path = APP_DIR / "static" / FIRST_EXERCISE.audio_file
    with wave.open(str(audio_path), "rb") as audio:
        assert 2 < audio.getnframes() / audio.getframerate() < 20
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
    response = client.get(
        "/static/" + FIRST_EXERCISE.audio_file, headers={"Range": "bytes=0-43"}
    )
    assert response.status_code == 206
    assert response.content[:4] == b"RIFF"
    assert len(response.content) == 44


def test_templates_and_assets_do_not_depend_on_working_directory(client, monkeypatch):
    """Serve templates and static assets even after the working directory changes."""
    monkeypatch.chdir(APP_DIR / "static")
    assert client.get(URL).status_code == 200
    assert client.get("/static/styles.css").status_code == 200
