"""Run the teacher prompt on new cases: python -m scripts.evaluate_tutor."""

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.exercises import Exercise
from app.tutor import (
    OPTIONS,
    PROMPT,
    PROMPT_VERSION,
    SCHEMA,
    parse_tutor,
    prepare_tutor_input,
    request_tutor,
)
from scripts.evaluate_local_ai import api

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "tutor_cases.json"


def main():
    """Save raw tutor responses and timings for separate development and holdout runs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=["development", "holdout"], required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    cases = [
        case
        for case in json.loads(CASES.read_text(encoding="utf-8"))
        if case["split"] == args.split
    ]
    prepared = []
    for case in cases:
        exercise = Exercise(
            id=case["id"],
            title="Evaluation",
            topic="Software teamwork",
            level=1,
            transcript=case["transcript"],
            translation_ru=case["translation_ru"],
            audio_file="",
        )
        prepared.append((case, prepare_tutor_input(exercise, case["answer"])))
    if args.check_only:
        print(f"Prepared {len(prepared)} {args.split} cases without model calls.")
        return 0
    metadata = {
        "type": "metadata",
        "prompt_version": PROMPT_VERSION,
        "prompt": PROMPT,
        "schema": SCHEMA,
        "options": OPTIONS,
        "split": args.split,
        "think": False,
        "timeout_seconds": 90,
        "fixtures_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest(),
        "ollama": api("/api/version", timeout=5),
        "models": api("/api/tags", timeout=5),
        "source_sha256": hashlib.sha256(
            (ROOT / "app" / "tutor.py").read_bytes()
        ).hexdigest(),
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / "var" / "evals" / f"tutor-{args.split}-{stamp}.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    errors = 0
    print(output, flush=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        stream.flush()
        for case, data in prepared:
            started = time.perf_counter()
            record = {"case_id": case["id"], "input": data}
            try:
                response = request_tutor(data)
                record["response"] = response
                record["analysis"] = parse_tutor(response)
                record["status"] = "valid"
            except (OSError, ValueError, KeyError, TypeError) as error:
                errors += 1
                record.update(status="error", error=str(error))
            record["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            print(
                f"{case['id']}: {record['status']}, {record['elapsed_seconds']}s",
                flush=True,
            )
    print("Manual semantic review required; valid means structure only.")
    return int(errors > 0)


if __name__ == "__main__":
    raise SystemExit(main())
