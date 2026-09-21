"""Generate selected catalog recordings using the optional local Piper tool."""

import argparse
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.exercises import EXERCISES, FIRST_EXERCISE, get_exercise  # noqa: E402


def main():
    """Generate selected exercise WAVs while preserving existing files by default."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", type=Path, required=True, help="Path to a Piper ONNX voice"
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--all", action="store_true", help="Select the whole catalog"
    )
    selection.add_argument(
        "--exercise", action="append", help="Exercise ID; may be repeated"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Replace existing audio"
    )
    args = parser.parse_args()
    exercises = (
        list(EXERCISES)
        if args.all
        else [
            get_exercise(identifier)
            for identifier in dict.fromkeys(args.exercise or [FIRST_EXERCISE.id])
        ]
    )
    if any(exercise is None for exercise in exercises):
        parser.error("Unknown exercise ID")
    from piper import PiperVoice

    voice = PiperVoice.load(str(args.model))
    for exercise in exercises:
        output = ROOT / "app" / "static" / exercise.audio_file
        if output.exists() and not args.overwrite:
            print(f"Skipped existing {output.name}")
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output), "wb") as audio:
            voice.synthesize_wav(exercise.transcript, audio)
        with wave.open(str(output), "rb") as audio:
            duration = audio.getnframes() / audio.getframerate()
            print(
                f"Generated {output.name}: {duration:.2f}s, {audio.getframerate()} Hz",
                flush=True,
            )


if __name__ == "__main__":
    main()
