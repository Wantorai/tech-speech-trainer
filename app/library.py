"""Store a bounded generated library and durable one-ahead training selections."""

import json
import random
import re
import time
from contextlib import contextmanager
from dataclasses import asdict

from app.exercises import EXERCISES, Exercise
from app.generation import fingerprint
from app.history import connect, database_path

CAPACITY = 10


@contextmanager
def library_connection():
    """Initialize library tables beside immutable attempt snapshots."""
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS generated_exercises (
            id TEXT PRIMARY KEY, topic TEXT NOT NULL, level INTEGER NOT NULL,
            payload TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
            completed REAL, metadata TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS training_groups (
            topic TEXT NOT NULL, level INTEGER NOT NULL,
            current_id TEXT, ready_id TEXT, status TEXT NOT NULL DEFAULT 'idle',
            PRIMARY KEY(topic, level))""")
        yield db


def audio_path(identifier: str):
    """Resolve only application-generated identifiers inside the local audio folder."""
    if not re.fullmatch(r"gen-[0-9a-f]{32}", identifier):
        raise ValueError("Invalid generated identifier")
    return database_path().resolve().parent / "generated-audio" / f"{identifier}.wav"


def generated_exercises() -> tuple[Exercise, ...]:
    """List playable generated records without exposing draft or partial audio files."""
    with library_connection() as db:
        rows = db.execute(
            "SELECT payload FROM generated_exercises ORDER BY rowid"
        ).fetchall()
    return tuple(Exercise(**json.loads(row[0])) for row in rows)


def find_generated(identifier: str) -> Exercise | None:
    """Find a generated exercise by its opaque identifier."""
    with library_connection() as db:
        row = db.execute(
            "SELECT payload FROM generated_exercises WHERE id=?", (identifier,)
        ).fetchone()
    return Exercise(**json.loads(row[0])) if row else None


def group_state(topic: str, level: int) -> dict:
    """Return the current background status and protected selections for a group."""
    with library_connection() as db:
        row = db.execute(
            "SELECT * FROM training_groups WHERE topic=? AND level=?", (topic, level)
        ).fetchone()
    return (
        dict(row) if row else {"current_id": None, "ready_id": None, "status": "idle"}
    )


def set_status(topic: str, level: int, status: str):
    """Record a small user-facing generation status without raw provider output."""
    with library_connection() as db:
        db.execute(
            "INSERT INTO training_groups(topic,level,status) VALUES(?,?,?) ON CONFLICT(topic,level) DO UPDATE SET status=excluded.status",
            (topic, level, status),
        )


def replacement(db, topic: str, level: int):
    """Select the least recently completed unprotected record when a group is full."""
    rows = db.execute(
        "SELECT id,completed FROM generated_exercises WHERE topic=? AND level=? ORDER BY completed",
        (topic, level),
    ).fetchall()
    protected = {
        value
        for row in db.execute("SELECT current_id,ready_id FROM training_groups")
        for value in row
        if value
    }
    if len(rows) < CAPACITY:
        return True, None
    candidate = next(
        (
            row["id"]
            for row in rows
            if row["completed"] is not None and row["id"] not in protected
        ),
        None,
    )
    return candidate is not None, candidate


def can_generate(topic: str, level: int) -> bool:
    """Pause generation when one item is ready or no completed slot can be replaced."""
    with library_connection() as db:
        state = db.execute(
            "SELECT ready_id FROM training_groups WHERE topic=? AND level=?",
            (topic, level),
        ).fetchone()
        return not (state and state[0]) and replacement(db, topic, level)[0]


def publish(exercise: Exercise, metadata: dict) -> bool:
    """Atomically publish complete audio and replace only an eligible completed item."""
    if not audio_path(exercise.id).is_file():
        raise ValueError("Audio must exist before publication")
    removed = None
    with library_connection() as db:
        db.execute("BEGIN IMMEDIATE")
        state = db.execute(
            "SELECT ready_id FROM training_groups WHERE topic=? AND level=?",
            (exercise.topic, exercise.level),
        ).fetchone()
        allowed, removed = replacement(db, exercise.topic, exercise.level)
        if not allowed or (state and state[0]):
            return False
        db.execute(
            "INSERT INTO generated_exercises(id,topic,level,payload,fingerprint,metadata) VALUES(?,?,?,?,?,?)",
            (
                exercise.id,
                exercise.topic,
                exercise.level,
                json.dumps(asdict(exercise), ensure_ascii=False),
                fingerprint(exercise.transcript),
                json.dumps(metadata, ensure_ascii=False),
            ),
        )
        if removed:
            db.execute("DELETE FROM generated_exercises WHERE id=?", (removed,))
        db.execute(
            "INSERT INTO training_groups(topic,level,ready_id,status) VALUES(?,?,?,'ready') ON CONFLICT(topic,level) DO UPDATE SET ready_id=excluded.ready_id,status='ready'",
            (exercise.topic, exercise.level, exercise.id),
        )
    if removed:
        try:
            audio_path(removed).unlink(missing_ok=True)
        except OSError:
            pass  # Retry orphan cleanup at the next application startup.
    return True


def choose_exercise(topic: str, level: int) -> Exercise:
    """Consume a ready item or randomly choose an unseen item before replaying others."""
    with library_connection() as db:
        db.execute("BEGIN IMMEDIATE")
        # A changed training group releases the old prefetch into the normal library.
        db.execute(
            "UPDATE training_groups SET ready_id=NULL, status='idle' WHERE topic != ? OR level != ?",
            (topic, level),
        )
        state = db.execute(
            "SELECT current_id,ready_id FROM training_groups WHERE topic=? AND level=?",
            (topic, level),
        ).fetchone()
        current, ready = tuple(state) if state else (None, None)
        saved = [
            Exercise(**json.loads(row[0]))
            for row in db.execute(
                "SELECT payload FROM generated_exercises WHERE topic=? AND level=?",
                (topic, level),
            )
        ]
        choices = [
            item
            for item in (*EXERCISES, *saved)
            if item.topic == topic and item.level == level and item.id != current
        ]
        seen = {
            row[0]
            for row in db.execute(
                "SELECT DISTINCT json_extract(exercise_json,'$.id') FROM attempts"
            )
        }
        chosen = next((item for item in choices if item.id == ready), None)
        if chosen is None:
            chosen = random.SystemRandom().choice(
                [item for item in choices if item.id not in seen] or choices
            )
        db.execute(
            "INSERT INTO training_groups(topic,level,current_id,status) VALUES(?,?,?,'idle') ON CONFLICT(topic,level) DO UPDATE SET current_id=excluded.current_id,ready_id=NULL,status='idle'",
            (topic, level, chosen.id),
        )
    return chosen


def protect_exercise(exercise: Exercise):
    """Protect the most recently opened exercise in each topic and level."""
    with library_connection() as db:
        db.execute(
            "INSERT INTO training_groups(topic,level,current_id) VALUES(?,?,?) ON CONFLICT(topic,level) DO UPDATE SET current_id=excluded.current_id,ready_id=CASE WHEN ready_id=excluded.current_id THEN NULL ELSE ready_id END",
            (exercise.topic, exercise.level, exercise.id),
        )


def mark_completed(identifier: str):
    """Make a generated item eligible for future replacement after an answer is saved."""
    with library_connection() as db:
        db.execute(
            "UPDATE generated_exercises SET completed=? WHERE id=?",
            (time.time(), identifier),
        )


def cleanup_audio():
    """Remove only owned orphan WAVs left by interrupted generation or replacement."""
    known = {item.id for item in generated_exercises()}
    folder = database_path().resolve().parent / "generated-audio"
    for path in folder.glob("gen-*.wav"):
        if re.fullmatch(r"gen-[0-9a-f]{32}", path.stem) and path.stem not in known:
            path.unlink(missing_ok=True)
    with library_connection() as db:
        db.execute("UPDATE training_groups SET status='idle' WHERE status='generating'")
