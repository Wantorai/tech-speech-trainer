"""Generate local drafts: python -m scripts.generate_exercise --topic 1 --level 1."""

import argparse
import json
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

from app.exercises import TOPIC_ORDER
from app.generation import (
    OPTIONS,
    PROMPT,
    PROMPT_VERSION,
    SCHEMA,
    prepare_generation,
    request_draft,
    validate_draft,
)

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Log reproducible raw drafts for manual review before catalog integration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--topic",
        type=int,
        choices=(1, 2, 3),
        required=True,
        help="1: experience, 2: projects, 3: teamwork",
    )
    parser.add_argument("--level", type=int, choices=(1, 2, 3, 4), required=True)
    parser.add_argument("--count", type=int, choices=range(1, 7), default=1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else secrets.randbelow(2**31 - 6)
    prepared = [
        (
            seed + i,
            prepare_generation(TOPIC_ORDER[args.topic - 1], args.level, seed + i),
        )
        for i in range(args.count)
    ]
    if args.check_only:
        print(json.dumps(prepared, ensure_ascii=False, indent=2))
        return 0
    folder = ROOT / "var" / "generated-drafts"
    folder.mkdir(parents=True, exist_ok=True)
    previous = []
    for path in folder.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("status") == "validated_draft":
            previous.append(record["draft"]["transcript"])
    failures = 0
    for current_seed, data in prepared:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        record = {
            "prompt_version": PROMPT_VERSION,
            "prompt": PROMPT,
            "model": "qwen3:4b",
            "seed": current_seed,
            "options": {**OPTIONS, "seed": current_seed},
            "schema": SCHEMA,
            "think": False,
            "timeout_seconds": 120,
            "input": data,
            "review_status": "pending",
        }
        started = time.perf_counter()
        try:
            record["response"] = request_draft(data, current_seed)
            record["draft"] = validate_draft(
                record["response"], args.level, tuple(previous)
            )
            previous.append(record["draft"]["transcript"])
            record["status"] = "validated_draft"
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures += 1
            record.update(status="rejected", error=str(error))
        record["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        output = folder / f"draft-{stamp}.json"
        output.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"{record['status']}: {output} ({record['elapsed_seconds']}s)", flush=True
        )
    print("Drafts need language and topic review; no audio or catalog entries created.")
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
