"""Generate the bundled first exercise using the optional local Piper tool."""

import argparse
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.exercises import FIRST_EXERCISE  # noqa: E402


def main():
    """Generate the first exercise WAV using the supplied Piper voice model."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", type=Path, required=True, help="Path to a Piper ONNX voice"
    )
    args = parser.parse_args()
    from piper import PiperVoice

    output = ROOT / "app" / "static" / FIRST_EXERCISE.audio_file
    output.parent.mkdir(parents=True, exist_ok=True)
    voice = PiperVoice.load(str(args.model))
    with wave.open(str(output), "wb") as audio:
        voice.synthesize_wav(FIRST_EXERCISE.transcript, audio)
    with wave.open(str(output), "rb") as audio:
        duration = audio.getnframes() / audio.getframerate()
        print(f"Generated {output.name}: {duration:.2f}s, {audio.getframerate()} Hz")


if __name__ == "__main__":
    main()
