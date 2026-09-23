"""Persist immutable attempt snapshots in a local SQLite database."""

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.exercises import Exercise
from app.feedback import Feedback


def database_path() -> Path:
    """Resolve the shared local database independently of the working directory."""
    return Path(
        os.environ.get(
            "TECHSPEECH_DB",
            Path(__file__).resolve().parent.parent / "var" / "attempts.sqlite3",
        )
    )


@contextmanager
def connect():
    """Open a short-lived transaction and initialize the local attempt table."""
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                exercise_version TEXT NOT NULL,
                exercise_json TEXT NOT NULL,
                answer TEXT NOT NULL,
                feedback_json TEXT NOT NULL
            )""")
            yield connection
    finally:
        connection.close()


def save_attempt(exercise: Exercise, answer: str, feedback: Feedback) -> int:
    """Save the submitted answer with exercise and deterministic feedback snapshots."""
    snapshot = json.dumps(asdict(exercise), ensure_ascii=False, sort_keys=True)
    version = hashlib.sha256(snapshot.encode()).hexdigest()
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO attempts (created_at, exercise_version, exercise_json, answer, feedback_json) VALUES (?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                version,
                snapshot,
                answer,
                json.dumps(asdict(feedback), ensure_ascii=False),
            ),
        )
        return cursor.lastrowid


def decode_attempt(row) -> dict:
    """Decode a stored snapshot without recomputing its original score."""
    attempt = dict(row)
    attempt["exercise"] = json.loads(attempt.pop("exercise_json"))
    attempt["feedback"] = json.loads(attempt.pop("feedback_json"))
    return attempt


def list_attempts(page: int, size: int = 20) -> tuple[list[dict], bool]:
    """Return one newest-first page and whether another page exists."""
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM attempts ORDER BY id DESC LIMIT ? OFFSET ?",
            (size + 1, (page - 1) * size),
        ).fetchall()
    return [decode_attempt(row) for row in rows[:size]], len(rows) > size


def get_attempt(attempt_id: int) -> dict | None:
    """Load an immutable attempt snapshot by its local identifier."""
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
    return decode_attempt(row) if row else None
