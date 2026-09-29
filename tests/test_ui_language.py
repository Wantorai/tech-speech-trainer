"""Verify English interface labels, progress counters, and preparation states."""

from fastapi.testclient import TestClient

from app.exercises import FIRST_EXERCISE
from app.main import app


def test_main_pages_use_english_interface_and_keep_only_translation_russian():
    """Render public pages in English while retaining the exercise translation."""
    with TestClient(app) as client:
        pages = [client.get("/"), client.get("/exercises"), client.get("/history")]
        result = client.post(
            f"/exercises/{FIRST_EXERCISE.id}",
            data={"answer": FIRST_EXERCISE.transcript},
        )
        pages.append(result)
    for page in pages:
        assert page.status_code == 200
        assert "Start training" in page.text or "Exercise" in page.text
        assert "Начать тренировку" not in page.text
        assert "История попыток" not in page.text
    assert FIRST_EXERCISE.translation_ru in pages[-1].text


def test_progress_counts_unique_completed_exercises_and_shows_limit():
    """Increase progress once per exercise and expose the permanent plus AI limit."""
    with TestClient(app) as client:
        before = client.get("/exercises").text
        assert "0 of 24" in before
        client.post(
            f"/exercises/{FIRST_EXERCISE.id}",
            data={"answer": FIRST_EXERCISE.transcript},
        )
        client.post(
            f"/exercises/{FIRST_EXERCISE.id}",
            data={"answer": FIRST_EXERCISE.transcript},
        )
        after = client.get("/history").text
    assert "1 of 24" in after
    assert "24 permanent + 120 AI exercises" in after


def test_training_status_contains_working_and_ready_icon_states():
    """Expose a status endpoint whose states map to the clock and checkmark UI."""
    with TestClient(app) as client:
        response = client.get(
            "/training-status",
            params={"topic": FIRST_EXERCISE.topic, "level": FIRST_EXERCISE.level},
        )
        page = client.get(f"/exercises/{FIRST_EXERCISE.id}?training=1")
    assert response.status_code == 200
    assert response.json()["status"] in {
        "idle",
        "generating",
        "ready",
        "full",
        "unavailable",
    }
    assert "status-icon--working" in page.text
    assert "training.js" in page.text
