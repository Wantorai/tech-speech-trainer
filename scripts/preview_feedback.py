"""Preview the first exercise feedback: python -m scripts.preview_feedback."""

import argparse
import json
from dataclasses import asdict

from app.exercises import FIRST_EXERCISE
from app.feedback import build_feedback


def main():
    """Print deterministic feedback and optionally request local vocabulary notes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answer", required=True)
    parser.add_argument(
        "--ai", action="store_true", help="Request optional Ollama notes"
    )
    args = parser.parse_args()
    try:
        result = build_feedback(FIRST_EXERCISE.transcript, args.answer, use_ai=args.ai)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
