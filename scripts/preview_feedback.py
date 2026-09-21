"""Preview the first exercise feedback: python -m scripts.preview_feedback."""

import argparse
import json
from dataclasses import asdict

from app.exercises import FIRST_EXERCISE
from app.feedback import build_feedback
from app.tutor import ask_tutor


def main():
    """Print deterministic feedback and optionally request a full teacher analysis."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answer", required=True)
    parser.add_argument(
        "--ai", action="store_true", help="Request optional Ollama tutor analysis"
    )
    args = parser.parse_args()
    try:
        result = build_feedback(FIRST_EXERCISE.transcript, args.answer)
        output = {
            "comparison": asdict(result.comparison),
            "explanations": result.explanations,
        }
        if args.ai:
            output["tutor"] = asdict(ask_tutor(FIRST_EXERCISE, args.answer))
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
