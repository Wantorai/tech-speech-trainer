"""HTTP checks for the first real listening exercise, with no running AI."""

import wave

import pytest
from fastapi.testclient import TestClient

from app.exercises import FIRST_EXERCISE
from app.main import APP_DIR, app

URL = f"/exercises/{FIRST_EXERCISE.id}"


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_original_is_not_rendered_before_submission(client):
    response = client.get(URL)
    assert response.status_code == 200
    assert FIRST_EXERCISE.transcript not in response.text
    assert "<audio" in response.text and 'name="answer"' in response.text
    assert "result-panel" not in response.text


def test_correct_answer_reveals_original_and_perfect_score(client):
    response = client.post(URL, data={"answer": FIRST_EXERCISE.transcript})
    assert response.status_code == 200
    assert "100%" in response.text
    assert "Всё совпало!" in response.text
    assert FIRST_EXERCISE.transcript in response.text
    assert response.headers["cache-control"] == "no-store"
    assert FIRST_EXERCISE.transcript not in client.get(URL).text


@pytest.mark.parametrize("answer", ["", " \n\t", "...?!", "word " * 401])
def test_invalid_answer_shows_russian_error_without_revealing_original(client, answer):
    response = client.post(URL, data={"answer": answer})
    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert FIRST_EXERCISE.transcript not in response.text


def test_user_markup_is_escaped_in_the_answer_and_feedback(client):
    response = client.post(URL, data={"answer": '<script>alert("hello")</script>'})
    assert response.status_code == 200
    assert "<script>" not in response.text
    assert "&lt;script&gt;" in response.text


def test_unknown_exercise_is_not_silently_replaced(client):
    assert client.get("/exercises/missing").status_code == 404
    assert (
        client.post("/exercises/missing", data={"answer": "anything"}).status_code
        == 404
    )


def test_audio_is_bundled_and_supports_seeking(client):
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
    monkeypatch.chdir(APP_DIR / "static")
    assert client.get(URL).status_code == 200
    assert client.get("/static/styles.css").status_code == 200
