"""The first reviewed exercise; transcripts are kept on the server."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Exercise:
    id: str
    title: str
    topic: str
    level: int
    transcript: str
    audio_file: str


FIRST_EXERCISE = Exercise(
    id="intro-01",
    title="Давайте познакомимся",
    topic="Знакомство и опыт работы",
    level=1,
    transcript=(
        "I work as a frontend developer and build applications for small businesses."
    ),
    audio_file="audio/intro-01.wav",
)


def get_exercise(exercise_id: str) -> Exercise | None:
    """Return the exercise matching the ID, or None if it is unknown."""
    return FIRST_EXERCISE if exercise_id == FIRST_EXERCISE.id else None
