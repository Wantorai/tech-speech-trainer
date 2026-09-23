"""Synthesize one generated transcript supplied through standard input."""

import argparse
import sys
import wave
from pathlib import Path


def main():
    """Load the local voice in an isolated process and write one WAV file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from piper import PiperVoice

    voice = PiperVoice.load(str(args.model))
    text = sys.stdin.buffer.read(8000).decode("utf-8")
    with wave.open(str(args.output), "wb") as audio:
        voice.synthesize_wav(text, audio)


if __name__ == "__main__":
    main()
