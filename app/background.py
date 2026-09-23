"""Prepare at most one exercise ahead while prioritizing interactive AI requests."""

import logging
import os
import secrets
import subprocess
import sys
import time
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Condition, Lock

from app.exercises import Exercise
from app.generation import (
    OPTIONS,
    PROMPT_VERSION,
    prepare_generation,
    request_draft,
    validate_draft,
)
from app.library import (
    audio_path,
    can_generate,
    generated_exercises,
    group_state,
    publish,
    set_status,
)

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)


class InferenceGate:
    """Serialize CPU-heavy work and admit waiting teacher requests before background jobs."""

    def __init__(self):
        """Initialize one shared resource slot and a teacher waiting count."""
        self.condition = Condition()
        self.busy = False
        self.teachers = 0

    @contextmanager
    def use(self, *, teacher=False):
        """Reserve the model or synthesizer with teacher priority at task boundaries."""
        with self.condition:
            if teacher:
                self.teachers += 1
            try:
                while self.busy or (not teacher and self.teachers):
                    self.condition.wait()
                self.busy = True
            finally:
                if teacher:
                    self.teachers -= 1
        try:
            yield
        finally:
            with self.condition:
                self.busy = False
                self.condition.notify_all()


INFERENCE = InferenceGate()


def synthesize(text: str, output: Path):
    """Run optional Piper in a bounded child process and verify the completed WAV."""
    model = Path(
        os.environ.get(
            "TECHSPEECH_VOICE", ROOT / "models/piper/en_US-ljspeech-high.onnx"
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.synthesize_generated",
            "--model",
            str(model),
            "--output",
            str(output),
        ],
        input=text,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=120,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    with wave.open(str(output), "rb") as audio:
        if (
            audio.getnchannels() != 1
            or audio.getsampwidth() != 2
            or not 1 < audio.getnframes() / audio.getframerate() < 120
        ):
            raise ValueError("Invalid synthesized audio")


class Generator:
    """Own a single background worker without an accumulating generation queue."""

    def __init__(self):
        """Create a lazy executor; no model request starts until a training transition."""
        self.pool = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="exercise-generator"
        )
        self.lock = Lock()
        self.future = None
        self.group = None
        self.closed = False

    def request(self, topic: str, level: int):
        """Schedule one preparation if no job or ready item already exists."""
        with self.lock:
            if self.closed:
                return
            if self.future and not self.future.done():
                if (
                    self.group == (topic, level)
                    and not group_state(topic, level)["ready_id"]
                ):
                    set_status(topic, level, "generating")
                return
            if not can_generate(topic, level):
                if not group_state(topic, level)["ready_id"]:
                    set_status(topic, level, "full")
                return
            set_status(topic, level, "generating")
            self.group = (topic, level)
            self.future = self.pool.submit(self.generate, topic, level)

    def generate(self, topic: str, level: int):
        """Publish a validated text/audio pair or retain the existing library on failure."""
        identifier = "gen-" + uuid.uuid4().hex
        output = audio_path(identifier)
        published = False
        started = time.perf_counter()
        seed = secrets.randbelow(2**31)
        try:
            if not can_generate(topic, level):
                set_status(
                    topic,
                    level,
                    "ready" if group_state(topic, level)["ready_id"] else "full",
                )
                return
            data = prepare_generation(topic, level, seed)
            with INFERENCE.use():
                response = request_draft(data, seed)
            draft = validate_draft(
                response,
                level,
                tuple(item.transcript for item in generated_exercises()),
                relaxed=True,
            )
            with INFERENCE.use():
                synthesize(draft["transcript"], output)
            exercise = Exercise(
                id=identifier,
                title="Рабочая ситуация · AI",
                topic=topic,
                level=level,
                transcript=draft["transcript"],
                translation_ru=draft["translation_ru"],
                audio_file=f"generated/{identifier}.wav",
            )
            published = publish(
                exercise,
                {
                    "prompt_version": PROMPT_VERSION,
                    "model": "qwen3:4b",
                    "seed": seed,
                    "options": OPTIONS,
                    "input": data,
                    "elapsed_seconds": round(time.perf_counter() - started, 3),
                    "prompt_tokens": response.get("prompt_eval_count"),
                    "output_tokens": response.get("eval_count"),
                },
            )
            if not published:
                set_status(topic, level, "full")
        except Exception:
            LOGGER.exception("Background exercise generation failed")
            set_status(topic, level, "unavailable")
        finally:
            if not published:
                output.unlink(missing_ok=True)

    def close(self):
        """Finish an active bounded task and stop the worker on application shutdown."""
        with self.lock:
            self.closed = True
        self.pool.shutdown(wait=True, cancel_futures=True)
