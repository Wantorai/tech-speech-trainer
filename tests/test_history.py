"""Verify durable attempt snapshots and history navigation without local AI."""

from dataclasses import replace
from html import unescape

from fastapi.testclient import TestClient

from app.exercises import FIRST_EXERCISE
from app.feedback import build_feedback
from app.history import get_attempt, list_attempts, save_attempt
from app.main import app

URL = f"/exercises/{FIRST_EXERCISE.id}"


def test_submission_survives_new_client_and_refresh():
    """Persist one submission across clients without duplicating it on GET refresh."""
    with TestClient(app) as client:
        response = client.post(
            URL, data={"answer": FIRST_EXERCISE.transcript}, follow_redirects=False
        )
        assert response.status_code == 303
        location = response.headers["location"]
    with TestClient(app) as client:
        for _ in range(2):
            response = client.get(location)
            assert response.status_code == 200
            assert "100%" in response.text
            assert response.headers["cache-control"] == "no-store"
        assert len(list_attempts(1)[0]) == 1
        assert "100%" in client.get("/history/1").text


def test_invalid_answers_do_not_create_attempts():
    """Keep invalid form submissions out of the learner's history."""
    with TestClient(app) as client:
        for answer in ("", "!!!", "x" * 2001):
            assert client.post(URL, data={"answer": answer}).status_code == 422
    assert list_attempts(1) == ([], False)


def test_snapshot_survives_exercise_changes(monkeypatch):
    """Preserve original wording and score when a catalog exercise is edited."""
    with TestClient(app) as client:
        client.post(URL, data={"answer": FIRST_EXERCISE.transcript})
        changed = replace(FIRST_EXERCISE, transcript="A different sentence.")
        monkeypatch.setattr("app.main.get_exercise", lambda _: changed)
        response = client.get(URL + "?attempt=1")
        assert response.url.path == "/history/1"
        assert FIRST_EXERCISE.transcript in unescape(response.text)
        assert "100%" in response.text
        assert 'id="ai-form"' not in response.text
    assert get_attempt(1)["exercise"]["transcript"] == FIRST_EXERCISE.transcript


def test_history_paginates_newest_first():
    """Bound history pages while retaining access to older attempts."""
    feedback = build_feedback(FIRST_EXERCISE.transcript, "hello")
    for _ in range(21):
        save_attempt(FIRST_EXERCISE, "hello", feedback)
    first, more = list_attempts(1)
    second, more_second = list_attempts(2)
    assert len(first) == 20 and first[0]["id"] == 21 and more
    assert len(second) == 1 and second[0]["id"] == 1 and not more_second
    with TestClient(app) as client:
        assert "Более старые" in client.get("/history").text
        assert "Более новые" in client.get("/history?page=2").text
        assert client.get("/history?page=0").status_code == 422


def test_missing_and_mismatched_attempts():
    """Reject missing records and attempts belonging to another exercise."""
    with TestClient(app) as client:
        assert "Здесь пока нет попыток" in client.get("/history").text
        assert client.get("/history/999").status_code == 404
        client.post(URL, data={"answer": "hello"})
        assert client.get("/exercises/intro-02?attempt=1").status_code == 404


def test_saved_answer_is_escaped_and_chat_is_not_stored():
    """Render submitted markup as text and exclude AI conversation fields."""
    answer = '<script>alert("hello")</script>'
    with TestClient(app) as client:
        client.post(URL, data={"answer": answer})
        response = client.get("/history/1")
        assert "<script>" not in response.text
        assert "&lt;script&gt;" in response.text
    saved = get_attempt(1)
    assert saved["answer"] == answer
    assert "chat" not in saved and "analysis" not in saved
    assert saved["feedback"]["ai_status"] == "not_requested"


def test_exercise_versions_are_stable_and_sensitive_to_edits():
    """Identify matching exercise metadata consistently and distinguish revisions."""
    feedback = build_feedback(FIRST_EXERCISE.transcript, "hello")
    first = save_attempt(FIRST_EXERCISE, "hello", feedback)
    second = save_attempt(FIRST_EXERCISE, "another answer", feedback)
    third = save_attempt(
        replace(FIRST_EXERCISE, translation_ru="Новый перевод"), "hello", feedback
    )
    assert (
        get_attempt(first)["exercise_version"]
        == get_attempt(second)["exercise_version"]
    )
    assert (
        get_attempt(first)["exercise_version"] != get_attempt(third)["exercise_version"]
    )
