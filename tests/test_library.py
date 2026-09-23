"""Verify bounded storage, nonblocking training, and background failure recovery."""

import json
import time
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.background import Generator, InferenceGate
from app.exercises import EXERCISES, TOPIC_ORDER, Exercise, get_exercise
from app.feedback import build_feedback
from app.generation import validate_draft
from app.history import get_attempt, save_attempt
from app.library import (
    audio_path,
    can_generate,
    choose_exercise,
    cleanup_audio,
    generated_exercises,
    group_state,
    mark_completed,
    protect_exercise,
    publish,
)
from app.main import app

TOPIC = TOPIC_ORDER[0]
TEXT = "I discuss confusing requirements with my colleagues before making any changes."


def provider_response(text=TEXT):
    """Build a complete fake generation response without contacting Ollama."""
    return {
        "done": True,
        "done_reason": "stop",
        "message": {
            "content": json.dumps(
                {
                    "transcript": text,
                    "translation_ru": "Я обсуждаю неясные требования с коллегами, прежде чем вносить изменения.",
                }
            )
        },
    }


def write_audio(text, output):
    """Create a small valid WAV without loading speech synthesis dependencies."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as audio:
        audio.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
        audio.writeframes(b"\x01\x00" * 44100)


def new_exercise(index=0, topic=TOPIC, level=1):
    """Create a distinct unpublished exercise with owned local test audio."""
    identifier = "gen-" + uuid.uuid4().hex
    exercise = Exercise(
        identifier,
        "AI test",
        topic,
        level,
        f"I reviewed task number {index} with my team before starting development.",
        "Я обсудил задачу с командой до начала разработки.",
        f"generated/{identifier}.wav",
    )
    write_audio(exercise.transcript, audio_path(identifier))
    return exercise


def fill_group(topic=TOPIC, level=1, offset=0):
    """Fill all ten slots while consuming ready items without marking them completed."""
    items = []
    for index in range(10):
        item = new_exercise(offset + index, topic, level)
        assert publish(item, {})
        assert choose_exercise(topic, level).id == item.id
        items.append(item)
    return items


def test_full_unplayed_group_pauses_then_replaces_oldest_completed():
    """Preserve unplayed items and historical results while rotating completed records."""
    items = fill_group()
    assert not can_generate(TOPIC, 1)
    attempt = save_attempt(
        items[0], "hello", build_feedback(items[0].transcript, "hello")
    )
    mark_completed(items[0].id)
    mark_completed(items[1].id)
    assert can_generate(TOPIC, 1)
    incoming = new_exercise(100)
    assert publish(incoming, {})
    assert len(generated_exercises()) == 10
    assert get_exercise(items[0].id) is None
    assert not audio_path(items[0].id).exists()
    assert get_exercise(items[1].id) is not None
    assert get_attempt(attempt)["exercise"]["transcript"] == items[0].transcript
    assert group_state(TOPIC, 1)["ready_id"] == incoming.id
    assert not can_generate(TOPIC, 1)


def test_current_item_is_never_replaced():
    """Keep the active item protected even when it is the only completed record."""
    items = fill_group()
    mark_completed(items[-1].id)
    assert not can_generate(TOPIC, 1)
    protect_exercise(EXERCISES[0])
    assert can_generate(TOPIC, 1)


def test_all_groups_have_separate_capacity_and_keep_prepared_items():
    """Bound the generated library to 120 items without changing the prepared catalog."""
    for index, topic in enumerate(TOPIC_ORDER):
        for level in range(1, 5):
            fill_group(topic, level, offset=index * 100 + level * 10)
    assert len(generated_exercises()) == 120
    assert len(EXERCISES) == 24
    for topic in TOPIC_ORDER:
        for level in range(1, 5):
            assert not can_generate(topic, level)


def test_generated_exercise_survives_restart_and_supports_attempts():
    """Serve persistent generated audio and scoring through the normal exercise routes."""
    item = new_exercise()
    assert publish(item, {})
    with TestClient(app) as client:
        page = client.get(f"/exercises/{item.id}?training=1")
        assert item.transcript not in page.text
        assert "/generated-audio/" in page.text
        result = client.post(
            f"/exercises/{item.id}?training=1", data={"answer": item.transcript}
        )
        assert "100%" in result.text and "training=1" in str(result.url)
        assert "Следующее упражнение" in result.text
        audio = client.get(
            f"/generated-audio/{item.id}.wav", headers={"Range": "bytes=0-43"}
        )
        assert audio.status_code == 206 and audio.content.startswith(b"RIFF")
    with TestClient(app) as client:
        assert client.get(f"/exercises/{item.id}").status_code == 200
        assert "100%" in client.get("/history/1").text
        assert item.id in client.get("/exercises").text


def test_staging_audio_and_path_traversal_are_not_served():
    """Do not serve unpublished files or arbitrary paths through the audio endpoint."""
    with TestClient(app) as client:
        item = new_exercise()
        assert client.get(f"/generated-audio/{item.id}.wav").status_code == 404
    with pytest.raises(ValueError):
        audio_path("../attempts.sqlite3")
    cleanup_audio()
    assert not audio_path(item.id).exists()


def test_training_remains_responsive_and_does_not_queue_generation():
    """Return library items while one generation runs and consume its ready result next."""
    entered, release = Event(), Event()

    def blocked_generation(*args):
        """Hold inference until normal navigation and status requests have completed."""
        entered.set()
        assert release.wait(10)
        return provider_response()

    with (
        patch(
            "app.background.request_draft", side_effect=blocked_generation
        ) as request,
        patch("app.background.synthesize", side_effect=write_audio),
        TestClient(app) as client,
    ):
        try:
            first = client.post("/train")
            assert first.status_code == 200 and entered.wait(3)
            second = client.post("/train")
            assert second.status_code == 200 and first.url.path != second.url.path
            assert client.get("/health").status_code == 200
            for _ in range(3):
                assert (
                    client.get(
                        "/training-status", params={"topic": TOPIC, "level": 1}
                    ).json()["status"]
                    == "generating"
                )
            assert request.call_count == 1
        finally:
            release.set()
        app.state.generator.future.result(timeout=5)
        ready = group_state(TOPIC, 1)["ready_id"]
        assert ready is not None
        with patch.object(app.state.generator, "request"):
            result = client.post("/train")
        assert result.url.path == f"/exercises/{ready}"
        assert request.call_count == 1


@pytest.mark.parametrize("failure", ["provider", "audio"])
def test_failure_preserves_existing_library_and_cleans_partial_audio(failure):
    """Keep saved items intact and remove partial outputs after either provider fails."""
    old = new_exercise()
    publish(old, {})
    choose_exercise(TOPIC, 1)

    def broken_audio(text, output):
        """Simulate synthesis that writes an incomplete file before failing."""
        write_audio(text, output)
        raise OSError("voice failed")

    with (
        patch(
            "app.background.request_draft",
            side_effect=TimeoutError() if failure == "provider" else None,
            return_value=provider_response(),
        ),
        patch("app.background.synthesize", side_effect=broken_audio),
    ):
        worker = Generator()
        try:
            worker.request(TOPIC, 1)
            worker.future.result(timeout=5)
        finally:
            worker.close()
    assert [item.id for item in generated_exercises()] == [old.id]
    assert list(audio_path(old.id).parent.glob("*.wav")) == [audio_path(old.id)]
    assert group_state(TOPIC, 1)["status"] == "unavailable"


def test_soft_lengths_accept_small_deviations_but_reject_extremes():
    """Allow approximate exercise lengths without accepting empty or oversized speech."""
    for level, count in ((1, 18), (2, 32), (3, 35), (4, 46)):
        assert validate_draft(
            provider_response(" ".join(["word"] * count) + "."), level, relaxed=True
        )
    for count in (2, 150):
        with pytest.raises(ValueError):
            validate_draft(
                provider_response(" ".join(["word"] * count) + "."), 1, relaxed=True
            )


def test_waiting_teacher_precedes_next_background_stage():
    """Give a waiting teacher the resource before another synthesis or generation stage."""
    gate = InferenceGate()
    order = []

    def use_resource(teacher):
        """Record the order in which contending tasks acquire the shared resource."""
        with gate.use(teacher=teacher):
            order.append("teacher" if teacher else "background")

    with ThreadPoolExecutor(max_workers=2) as pool:
        with gate.use():
            background = pool.submit(use_resource, False)
            teacher = pool.submit(use_resource, True)
            deadline = time.monotonic() + 3
            while gate.teachers == 0 and time.monotonic() < deadline:
                time.sleep(0.001)
            assert gate.teachers == 1
        teacher.result(timeout=3)
        background.result(timeout=3)
    assert order == ["teacher", "background"]


def test_training_rejects_unknown_groups_before_scheduling():
    """Validate topic and level before allowing a new background request."""
    with (
        TestClient(app) as client,
        patch.object(app.state.generator, "request") as request,
    ):
        for data in ({"topic": "unknown"}, {"level": "5"}, {"level": "oops"}):
            assert client.post("/train", data=data).status_code == 422
        request.assert_not_called()


def test_web_teacher_waits_for_generation_before_synthesis():
    """Queue one teacher behind active generation while health and normal checking stay responsive."""
    from app.background import INFERENCE
    from app.tutor import TutorResult

    entered, release = Event(), Event()
    order = []

    def blocked_generation(*args):
        """Hold the current model request until a teacher is waiting."""
        entered.set()
        assert release.wait(10)
        order.append("generation")
        return provider_response()

    def teacher_response(*args):
        """Record interactive inference without accessing a real model."""
        order.append("teacher")
        return TutorResult("unavailable")

    def recorded_audio(text, output):
        """Record the synthesis stage after waiting interactive inference."""
        order.append("audio")
        write_audio(text, output)

    with (
        patch("app.background.request_draft", side_effect=blocked_generation),
        patch("app.background.synthesize", side_effect=recorded_audio),
        patch("app.main.ask_tutor", side_effect=teacher_response),
        TestClient(app) as client,
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        try:
            client.post("/train")
            assert entered.wait(3)
            pending = pool.submit(
                client.post, "/exercises/intro-01/ai", data={"answer": "hello"}
            )
            deadline = time.monotonic() + 3
            while INFERENCE.teachers == 0 and time.monotonic() < deadline:
                time.sleep(0.001)
            assert INFERENCE.teachers == 1
            assert client.get("/health").status_code == 200
            assert (
                client.post("/exercises/intro-01", data={"answer": "hello"}).status_code
                == 200
            )
        finally:
            release.set()
        assert pending.result(timeout=5).status_code == 200
        app.state.generator.future.result(timeout=5)
    assert order == ["generation", "teacher", "audio"]


def test_changing_topic_releases_previous_ready_item_into_library():
    """Keep a prepared item reusable without reserving multiple future training slots."""
    item = new_exercise()
    assert publish(item, {})
    choose_exercise(TOPIC_ORDER[1], 2)
    assert group_state(TOPIC, 1)["ready_id"] is None
    assert get_exercise(item.id) == item
