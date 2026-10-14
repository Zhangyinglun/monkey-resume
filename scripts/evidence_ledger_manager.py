#!/usr/bin/env python3
"""Prepare model-led source imports and commit validated candidate transactions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.candidate_cache import (  # noqa: E402
    commit_import,
    load_candidate_context,
    prepare_import,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "commit", "show", "context"))
    parser.add_argument("--workspace", type=Path, default=Path.home() / "Documents/MonkeyResume")
    parser.add_argument("--input", type=Path)
    parser.add_argument(
        "--source-type", choices=("document", "candidate_response"), default="document"
    )
    parser.add_argument("--source-id")
    parser.add_argument(
        "--event-id", help="Stable candidate-answer event ID for retry deduplication"
    )
    parser.add_argument("--proposal", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            if not args.input:
                raise ValueError("prepare requires --input")
            result = prepare_import(
                args.workspace, args.input, source_type=args.source_type, event_id=args.event_id
            )
        elif args.action == "commit":
            if not args.source_id or not args.proposal:
                raise ValueError("commit requires --source-id and --proposal")
            proposal = json.loads(args.proposal.expanduser().read_text(encoding="utf-8"))
            result = commit_import(args.workspace, args.source_id, proposal)
        else:
            result = load_candidate_context(args.workspace)
    except (ValueError, OSError, RuntimeError) as exc:
        print(
            json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
