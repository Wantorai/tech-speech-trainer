"""HTTP checks for optional AI notes without a running model."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.exercises import FIRST_EXERCISE
from app.main import app

URL = "/exercises/intro-01"
ANSWER = "I work as a developer and build applications for small businesses."


@pytest.fixture
def client():
    """Provide a client with the application lifespan active."""
    with TestClient(app) as client:
        yield client


def test_check_renders_explanations_and_ai_for_the_submitted_answer(client):
    """Show deterministic feedback immediately without calling the model."""
    with patch("app.feedback.request_notes") as request:
        response = client.post(URL, data={"answer": ANSWER})
    request.assert_not_called()
    assert "91.7%" in response.text
    assert "В ответе пропущено «frontend»." in response.text
    assert 'id="ai-form"' in response.text
    assert f'value="{ANSWER}"' in response.text
    assert FIRST_EXERCISE.translation_ru in response.text
    assert 'id="ai-form"' not in client.get(URL).text
    perfect = client.post(URL, data={"answer": FIRST_EXERCISE.transcript})
    assert 'id="ai-form"' not in perfect.text


def test_ai_endpoint_returns_notes_without_score_or_transcript(client):
    """Expose validated notes separately from the existing exercise result."""
    response = {
        "done": True,
        "done_reason": "stop",
        "message": {
            "content": json.dumps(
                {
                    "notes": [
                        {
                            "word": "frontend",
                            "meaning_ru": "Интерфейс <script>alert(1)</script>",
                        }
                    ]
                }
            )
        },
    }
    with patch("app.feedback.request_notes", return_value=response):
        result = client.post(URL + "/ai", data={"answer": ANSWER})
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    assert set(result.json()) == {"status", "message", "notes"}
    assert result.json()["status"] == "ready"
    assert result.json()["notes"][0]["word"] == "frontend"


@pytest.mark.parametrize(
    "error,status",
    [
        (TimeoutError(), "timeout"),
        (OSError(), "unavailable"),
        (ValueError(), "invalid_response"),
    ],
)
def test_failures_return_readable_status_and_release_lock(client, error, status):
    """Allow a new request after provider failure without losing normal checking."""
    with patch("app.feedback.request_notes", side_effect=error):
        for _ in range(2):
            response = client.post(URL + "/ai", data={"answer": ANSWER})
            assert response.json()["status"] == status
            assert "Результат проверки сохранён" in response.json()["message"]
    assert "91.7%" in client.post(URL, data={"answer": ANSWER}).text


@pytest.mark.parametrize("answer", ["", "...", "x" * 2001])
def test_invalid_ai_input_never_calls_provider(client, answer):
    """Validate AI requests independently of the browser controls."""
    with patch("app.feedback.request_notes") as request:
        assert client.post(URL + "/ai", data={"answer": answer}).status_code == 422
        assert (
            client.post("/exercises/unknown/ai", data={"answer": "hello"}).status_code
            == 404
        )
    request.assert_not_called()


def test_correct_answer_skips_provider_even_on_direct_ai_request(client):
    """Skip inference for a perfect answer submitted directly to the AI endpoint."""
    with patch("app.feedback.request_notes") as request:
        response = client.post(URL + "/ai", data={"answer": FIRST_EXERCISE.transcript})
    request.assert_not_called()
    assert response.json()["status"] == "not_needed"


def test_pending_ai_does_not_block_health_or_queue_another_inference(client):
    """Keep ordinary HTTP requests responsive while one model call is pending."""
    entered, release = Event(), Event()

    def wait_for_release(*args, **kwargs):
        """Hold a fake provider call until concurrent requests have been checked."""
        entered.set()
        assert release.wait(5)
        raise TimeoutError()

    with (
        patch("app.feedback.request_notes", side_effect=wait_for_release),
        ThreadPoolExecutor() as pool,
    ):
        pending = pool.submit(client.post, URL + "/ai", data={"answer": ANSWER})
        try:
            assert entered.wait(3)
            health = pool.submit(client.get, "/health").result(timeout=2)
            assert health.status_code == 200
            busy = pool.submit(
                client.post, URL + "/ai", data={"answer": ANSWER}
            ).result(timeout=2)
            assert busy.status_code == 429
            assert busy.json()["status"] == "busy"
        finally:
            release.set()
        assert pending.result(timeout=3).json()["status"] == "timeout"
