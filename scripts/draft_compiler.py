#!/usr/bin/env python3
"""Compile one model-authored draft into a traceable display projection.

This validates references and structural ownership, not semantic entailment.
No text, metric or tool heuristic can certify that a paraphrase is truthful.
"""

from __future__ import annotations

import argparse
import copy
import re
import sys
from difflib import ndiff
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.resume_shared import (  # noqa: E402
    add_workspace_argument,
    canonical_json_fingerprint,
    iter_resume_text_fields,
    load_json_file,
    validate_resume_content,
    write_json_file,
)

_SECTIONS = {
    "experience": ("employment", {"company", "title", "dates", "location", "bullets"}),
    "education": ("education", {"school", "degree", "dates", "location"}),
    "projects": ("project", {"name", "tech", "dates", "bullets"}),
    "certifications": ("certification", {"name", "issuer", "dates", "bullets"}),
    "awards": ("award", {"name", "organization", "dates", "bullets"}),
    "skills": ("skill", {"category", "items"}),
}
LIMITATIONS = (
    "Traceability only: bindings do not certify semantic entailment, metric-object "
    "truth, completeness, JD suitability, or publication readiness. Independent "
    "semantic and rendered-document review is required."
)


def _object(value: Any, path: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    return value


def _array(value: Any, path: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be an array")
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-empty string")
    return value


def _ids(value: Any, path: str) -> list[str]:
    result = _array(value, path)
    if not result:
        raise ValueError(f"{path} must contain claim IDs")
    for item in result:
        _text(item, path)
    if len(set(result)) != len(result):
        raise ValueError(f"{path} contains duplicate IDs")
    return result


def load_candidate_context(workspace: Path) -> dict:
    """Load the shared v2 cache context; never fall back to old snapshots."""
    from scripts.candidate_cache import load_candidate_context as load

    return load(workspace)


def _validate_target(target: dict) -> None:
    # The JD is literal original text, not a path or an interpreted analysis.
    _text(target.get("original_jd"), "target.original_jd (original UTF-8 text)")
    seen: set[str] = set()
    for i, requirement in enumerate(_array(target.get("requirements"), "target.requirements")):
        item = _object(requirement, f"target.requirements[{i}]")
        rid = _text(item.get("id"), f"target.requirements[{i}].id")
        _text(item.get("text"), f"target.requirements[{i}].text")
        if not isinstance(item.get("priority"), str) or item["priority"] not in {"P1", "P2", "P3"}:
            raise ValueError(f"target.requirements[{i}].priority must be P1, P2 or P3")
        if rid in seen:
            raise ValueError(f"duplicate requirement id: {rid}")
        seen.add(rid)
    for key in ("company", "role", "job_url"):
        if key in target and target[key] is not None and not isinstance(target[key], str):
            raise ValueError(f"target.{key} must be a string or null")


def _validate_display(resume: dict) -> None:
    validate_resume_content(resume, require_non_empty=True)
    unknown = set(resume) - {"name", "contact", "project_heading", *_SECTIONS}
    if unknown:
        raise ValueError(f"unknown resume display fields: {sorted(unknown)}")
    _text(resume["name"], "resume.name")
    for section, (_, allowed) in _SECTIONS.items():
        for i, item in enumerate(resume.get(section, [])):
            if set(item) - allowed:
                raise ValueError(f"unknown display fields in {section}[{i}]")
            if section == "skills":
                _text(item["category"], f"skills[{i}].category")
                # Skill terms use item-level evidence paths.
                _array(item["items"], f"skills[{i}].items")
                for j, text in enumerate(item["items"]):
                    _text(text, f"skills[{i}].items[{j}]")
                    if text != text.strip():
                        raise ValueError(
                            f"skills[{i}].items[{j}] must not have surrounding whitespace"
                        )
            else:
                for key, value in item.items():
                    if key == "bullets":
                        for j, text in enumerate(value):
                            _text(text, f"{section}[{i}].bullets[{j}]")
                    else:
                        _text(value, f"{section}[{i}].{key}")


def compile_draft(draft: dict, context: dict) -> dict:
    """Pure v2 draft compiler. Invalid bindings raise descriptive ValueError."""
    draft = _object(draft, "draft")
    context = _object(context, "context")
    for label, value in (("draft", draft), ("context", context)):
        if type(value.get("schema_version")) is not int or value["schema_version"] != 2:
            raise ValueError(f"{label}.schema_version must be 2")
    context_id = _text(context.get("context_id"), "context.context_id")
    if not context_id.startswith("sha256:"):
        raise ValueError("context.context_id must be a sha256 fingerprint")
    if draft.get("context_id") != context_id:
        raise ValueError("stale draft context_id; reload candidate context and rebind draft")
    candidate_id = _text(context.get("candidate_id"), "context.candidate_id")
    if "candidate_id" in draft and draft["candidate_id"] != candidate_id:
        raise ValueError("draft candidate_id differs from context")
    target = _object(draft.get("target"), "draft.target")
    _validate_target(target)
    target = copy.deepcopy(target)
    for key in ("company", "role", "job_url"):
        if key in target and target[key] is None:
            target[key] = ""
    resume = _object(draft.get("resume"), "draft.resume")
    _validate_display(resume)
    links = _object(draft.get("evidence_links"), "draft.evidence_links")
    ledger = _object(context.get("ledger"), "context.ledger")
    active_ids = set(_ids(context.get("active_claim_ids"), "context.active_claim_ids"))
    entities: dict[str, dict] = {}
    claims: dict[str, tuple[dict, dict]] = {}
    for raw in _array(ledger.get("entities"), "ledger.entities"):
        entity = _object(raw, "ledger entity")
        eid = _text(entity.get("entity_id"), "entity.entity_id")
        if eid in entities:
            raise ValueError(f"duplicate entity_id: {eid}")
        entities[eid] = entity
        for raw_claim in _array(entity.get("claims"), f"{eid}.claims"):
            claim = _object(raw_claim, "ledger claim")
            cid = _text(claim.get("claim_id"), "claim.claim_id")
            if cid in claims:
                raise ValueError(f"duplicate claim_id: {cid}")
            claims[cid] = (entity, claim)

    def usable(cid: str, path: str) -> tuple[dict, dict]:
        if cid not in claims:
            raise ValueError(f"{path}: unknown claim {cid}")
        entity, claim = claims[cid]
        if entity.get("state") != "active" or claim.get("status") != "active":
            raise ValueError(f"{path}: inactive claim/entity {cid}")
        if claim.get("polarity") != "positive":
            raise ValueError(f"{path}: negative or missing polarity for {cid}")
        if (
            claim.get("evidence_state") not in {"sourced", "candidate_confirmed"}
            or cid not in active_ids
        ):
            raise ValueError(f"{path}: unresolved or unusable evidence {cid}")
        _text(claim.get("claim_text"), f"claim {cid}.claim_text")
        if not _array(claim.get("provenance"), f"claim {cid}.provenance"):
            raise ValueError(f"{path}: claim {cid} has no provenance")
        return entity, claim

    anchors: dict[str, str] = {}
    for section, (kind, _) in _SECTIONS.items():
        if section == "skills":
            continue
        for i, _ in enumerate(resume.get(section, [])):
            path = f"{section}[{i}]"
            link = _object(links.get(path), f"{path} entity anchor")
            eid = _text(link.get("entity_id"), f"{path}.entity_id")
            entity = entities.get(eid)
            if (
                entity is None
                or entity.get("state") != "active"
                or entity.get("entity_type") != kind
            ):
                raise ValueError(f"{path}: unknown, inactive or wrong type entity anchor {eid}")
            if set(link) != {"entity_id"}:
                raise ValueError(f"{path}: entity anchor must only contain entity_id")
            anchors[path] = eid

    relationships: list[dict] = []
    relationship_ids: set[str] = set()
    for raw in _array(ledger.get("relationships"), "ledger.relationships"):
        relationship = _object(raw, "ledger relationship")
        rid = _text(relationship.get("relationship_id"), "relationship.relationship_id")
        if rid in relationship_ids:
            raise ValueError(f"duplicate relationship_id: {rid}")
        relationship_ids.add(rid)
        relationships.append(relationship)

    def ownership(project: str, employment: str, path: str) -> str:
        matches = [
            r
            for r in relationships
            if r.get("project_id") == project
            and r.get("employment_id") == employment
            and r.get("state") == "active"
            and isinstance(r.get("provenance"), list)
            and r["provenance"]
        ]
        if len(matches) != 1:
            raise ValueError(
                f"{path}: no unique active sourced project ownership relationship to {employment}"
            )
        return matches[0]["relationship_id"]

    profile = _object(context.get("profile"), "context.profile")
    selected_name = _text(profile.get("display_name_claim_id"), "profile.display_name_claim_id")
    name_entity, name_claim = usable(selected_name, "name")
    if (
        name_entity.get("entity_type") != "profile"
        or name_claim.get("field") != "name"
        or resume["name"] != context.get("display_name")
        or resume["name"] != name_claim["claim_text"]
    ):
        raise ValueError(
            "name must equal the resolved supported context display_name and selected name claim"
        )

    fields = list(iter_resume_text_fields(resume))
    entries: list[dict] = []
    categories: list[tuple[str, str]] = []
    used: set[str] = set()
    valid_paths = {path for path, _, _, _ in fields} | set(anchors)
    if set(links) - valid_paths:
        raise ValueError(
            f"evidence_links contains unknown display paths: {sorted(set(links) - valid_paths)}"
        )
    for path, text, _, key in fields:
        if re.fullmatch(r"skills\[\d+\]\.category", path):
            if path in links:
                raise ValueError(f"{path}: category is presentation metadata, not a claim")
            categories.append((path, text))
            continue
        anchor = anchors.get(key)
        structural = anchor is not None and ".bullets[" not in path
        field = path.rsplit(".", 1)[-1]
        if path in links:
            link = _object(links[path], path)
            if set(link) != {"claim_ids"}:
                raise ValueError(f"{path}: fact binding must only contain claim_ids")
            ids = _ids(link.get("claim_ids"), f"{path}.claim_ids")
            mode = "explicit"
        elif structural:
            ids = [
                cid
                for cid, (entity, claim) in claims.items()
                if entity["entity_id"] == anchor
                and cid in active_ids
                and claim.get("field") == field
                and claim.get("claim_text") == text
                and claim.get("status") == "active"
                and claim.get("polarity") == "positive"
            ]
            if len(ids) != 1:
                raise ValueError(
                    f"{path}: unbound field; cite modified or ambiguous structural text explicitly"
                )
            mode = "exact_structural"
        else:
            raise ValueError(f"{path}: unbound substantive field")
        supporting = [usable(cid, path) for cid in ids]
        eids: list[str] = []
        rids: list[str] = []
        for entity, claim in supporting:
            eid = entity["entity_id"]
            if path in {"name", "contact"} and entity.get("entity_type") != "profile":
                raise ValueError(f"{path}: contact/name must bind profile evidence")
            if path == "name" and ids != [selected_name]:
                raise ValueError("name must link the selected display_name claim only")
            if structural and (eid != anchor or claim.get("field") != field):
                raise ValueError(
                    f"{path}: structural identity requires relevant field on the anchored entity"
                )
            if anchor is not None and not structural and eid != anchor:
                if key.startswith("experience[") and entity.get("entity_type") == "project":
                    rids.append(ownership(eid, anchor, path))
                else:
                    raise ValueError(
                        f"{path}: claim belongs to wrong entity {eid}, expected {anchor}"
                    )
            eids.append(eid)
        used.update(ids)
        entries.append(
            {
                "projection_path": path,
                "rendered_text": text,
                "binding_mode": mode,
                "entity_ids": list(dict.fromkeys(eids)),
                "source_claim_ids": list(ids),
                "relationship_ids": list(dict.fromkeys(rids)),
                "claim_entity_ids": {
                    cid: entity["entity_id"] for cid, (entity, _) in zip(ids, supporting)
                },
            }
        )
    for path, text in categories:
        prefix = path.removesuffix("category") + "items["
        grouped = [entry for entry in entries if entry["projection_path"].startswith(prefix)]
        if not grouped:
            raise ValueError(f"{path}: skill category has no bound items")
        entries.append(
            {
                "projection_path": path,
                "rendered_text": text,
                "binding_mode": "presentation",
                "entity_ids": list(
                    dict.fromkeys(e for item in grouped for e in item["entity_ids"])
                ),
                "source_claim_ids": list(
                    dict.fromkeys(c for item in grouped for c in item["source_claim_ids"])
                ),
                "relationship_ids": [],
                "grouped_item_paths": [item["projection_path"] for item in grouped],
            }
        )

    if "project_heading" in resume:
        grouped = [entry for entry in entries if entry["projection_path"].startswith("projects[")]
        entries.append({
            "projection_path": "project_heading",
            "rendered_text": resume["project_heading"],
            "binding_mode": "presentation",
            "entity_ids": list(dict.fromkeys(e for item in grouped for e in item["entity_ids"])),
            "source_claim_ids": list(dict.fromkeys(c for item in grouped for c in item["source_claim_ids"])),
            "relationship_ids": [],
            "grouped_item_paths": [item["projection_path"] for item in grouped],
        })

    omitted: set[str] = set()
    omissions = _array(draft.get("omissions"), "draft.omissions")
    for i, raw in enumerate(omissions):
        omission = _object(raw, f"omissions[{i}]")
        _text(omission.get("reason"), f"omissions[{i}].reason (specific editorial reason)")
        for cid in _ids(omission.get("claim_ids"), f"omissions[{i}].claim_ids"):
            usable(cid, f"omissions[{i}]")
            if cid in used or cid in omitted:
                raise ValueError(f"omissions[{i}]: claim {cid} already included or omitted")
            omitted.add(cid)
    draft_hash = canonical_json_fingerprint(draft)
    resume_hash = canonical_json_fingerprint(resume)
    manifest = {
        "schema_version": 2,
        "context_id": context_id,
        "draft_fingerprint": draft_hash,
        "resume_fingerprint": resume_hash,
        "entries": sorted(entries, key=lambda entry: entry["projection_path"]),
        "unused_claim_ids": sorted(active_ids - used),
    }
    # Mechanical word comparisons are aids for evidence review, not judgments
    # that a rewrite preserves meaning or is a better sentence.
    text_changes = [
        {
            "projection_path": entry["projection_path"],
            "rendered_text": entry["rendered_text"],
            "binding_mode": entry["binding_mode"],
            "comparisons": [
                {
                    "source_claim_id": cid,
                    "source_text": claims[cid][1]["claim_text"],
                    "text_equal": claims[cid][1]["claim_text"] == entry["rendered_text"],
                    "diff": list(
                        ndiff(claims[cid][1]["claim_text"].split(), entry["rendered_text"].split())
                    ),
                }
                for cid in entry["source_claim_ids"]
            ],
        }
        for entry in manifest["entries"]
        if entry["binding_mode"] != "presentation"
    ]
    return copy.deepcopy(
        {
            "schema_version": 2,
            "context_id": context_id,
            "candidate_id": candidate_id,
            "draft_fingerprint": draft_hash,
            "resume_fingerprint": resume_hash,
            "resume": resume,
            "target": target,
            "manifest": manifest,
            "text_changes": text_changes,
            "omissions": omissions,
            "audit_scope": "traceability_only",
            "semantic_review_required": True,
            "limitations": LIMITATIONS,
        }
    )


def _external(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == PROJECT_ROOT or PROJECT_ROOT in resolved.parents:
        raise ValueError(f"candidate input/output must be outside the Skill repository: {resolved}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    initializer = commands.add_parser(
        "init", help="Initialize one editable draft from literal JD text"
    )
    add_workspace_argument(initializer)
    initializer.add_argument("--jd", type=Path, required=True)
    initializer.add_argument("--output", type=Path, required=True)
    compiler = commands.add_parser("compile", help="Compile draft bindings without publishing")
    add_workspace_argument(compiler)
    compiler.add_argument("--draft", type=Path, required=True)
    compiler.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        workspace = _external(args.workspace)
        context = load_candidate_context(workspace)
        if args.command == "init":
            output = _external(args.output)
            if output.exists():
                raise ValueError(f"refusing to overwrite existing draft: {output}")
            draft = {
                "schema_version": 2,
                "context_id": context["context_id"],
                "target": {
                    "original_jd": args.jd.expanduser().resolve().read_text(encoding="utf-8"),
                    "requirements": [],
                },
                "resume": {
                    "name": "",
                    "contact": "",
                    "skills": [],
                    "experience": [],
                    "education": [],
                },
                "evidence_links": {},
                "omissions": [],
            }
            write_json_file(output, draft)
            print(output)
        else:
            output_dir = _external(args.output_dir)
            compiled = compile_draft(load_json_file(args.draft.expanduser().resolve()), context)
            for filename, value in (
                ("compiled-draft.json", compiled),
                ("resume.json", compiled["resume"]),
                ("manifest.json", compiled["manifest"]),
            ):
                print(write_json_file(output_dir / filename, value))
            print(LIMITATIONS)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Error: draft compilation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
