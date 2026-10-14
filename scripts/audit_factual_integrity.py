#!/usr/bin/env python3
"""Audit v2 draft traceability, not semantic factual truth or publication QA."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.draft_compiler import (  # noqa: E402
    LIMITATIONS,
    _external,
    compile_draft,
    load_candidate_context,
)
from scripts.resume_shared import add_workspace_argument, load_json_file  # noqa: E402


def audit_draft(draft: dict, context: dict) -> dict:
    """Return deterministic reference findings; PASS means traceability only."""
    report = {
        "schema_version": 2,
        "verdict": "FAIL",
        "audit_scope": "traceability_only",
        "semantic_review_required": True,
        "limitations": LIMITATIONS,
        "findings": [],
    }
    try:
        compiled = compile_draft(draft, context)
    except ValueError as exc:
        report["findings"] = [
            {"code": "INVALID_DRAFT_TRACEABILITY", "severity": "ERROR", "message": str(exc)}
        ]
    else:
        report.update(
            verdict="PASS",
            context_id=compiled["context_id"],
            draft_fingerprint=compiled["draft_fingerprint"],
            resume_fingerprint=compiled["resume_fingerprint"],
            unused_claim_ids=compiled["manifest"]["unused_claim_ids"],
            covered_fields=len(compiled["manifest"]["entries"]),
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_workspace_argument(parser)
    parser.add_argument("--draft", type=Path, required=True, help="Model-authored v2 draft JSON")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    try:
        report = audit_draft(
            load_json_file(args.draft.expanduser().resolve()),
            load_candidate_context(_external(args.workspace)),
        )
    except (OSError, ValueError) as exc:
        print(f"Error: traceability audit failed: {exc}", file=sys.stderr)
        return 1
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Traceability audit: {report['verdict']} (traceability_only)")
        print(LIMITATIONS)
        for finding in report["findings"]:
            print(f"  {finding['message']}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
