"""Source-backed candidate transactions; no model or resume parser lives here."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from scripts.extract_resume_text import extract_resume_blocks
from scripts.file_lock import exclusive_file_lock

SCHEMA_VERSION = 2
REPOSITORY = Path(__file__).resolve().parent.parent
ENTITY_TYPES = {"profile", "employment", "project", "education", "skill", "certification", "award"}


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f"Unsafe symlink target: {part}")
        if os.name == "nt":
            try:
                attributes = part.lstat().st_file_attributes
            except FileNotFoundError:
                continue
            if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError(f"Unsafe reparse point target: {part}")


def validate_workspace(workspace: Path) -> Path:
    """Reject repository data and symlinked authoritative/import targets."""
    workspace = Path(workspace).expanduser().absolute()
    if workspace.is_symlink():
        raise ValueError(f"Unsafe symlink workspace: {workspace}")
    if os.name == "nt":
        _safe(workspace)
    # POSIX system prefixes can be aliases (macOS /var -> /private/var).
    # Canonicalize those before checking the authoritative cache paths.
    workspace = workspace.resolve()
    if workspace == REPOSITORY or REPOSITORY in workspace.parents:
        raise ValueError("Candidate workspace must be outside the Skill repository.")
    for name in (
        "cache",
        "cache/candidate-state.json",
        "cache/import.lock",
        "cache/imports",
        "cache/sources",
        "cache/state-history",
    ):
        _safe(workspace / name)
    return workspace


@contextmanager
def workspace_lock(workspace: Path) -> Iterator[Path]:
    workspace = validate_workspace(workspace)
    cache = workspace / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    with exclusive_file_lock(cache / "import.lock"):
        yield workspace


def _read(path: Path) -> dict:
    _safe(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _write(path: Path, value: dict) -> None:
    """Fsync then replace a single JSON file; failed replacement leaves old state."""
    _safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".transaction-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _state(workspace: Path) -> dict:
    path = workspace / "cache/candidate-state.json"
    if not path.exists():
        for name in (
            "candidate-evidence.json",
            "candidate-profile.json",
            "base-resume.json",
            "resume-working.json",
        ):
            if (workspace / "cache" / name).exists():
                raise ValueError(
                    "Legacy workspace requires deliberate migration or a new workspace."
                )
        return {
            "schema_version": 2,
            "candidate_id": None,
            "ledger": {"entities": [], "relationships": [], "conflicts": []},
            "profile": {"preferences": {}, "display_name_claim_id": None},
            "sources": [],
        }
    state = _read(path)
    if type(state.get("schema_version")) is not int or state["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported candidate state schema; deliberate migration required.")
    if not isinstance(state.get("ledger"), dict) or not isinstance(state.get("profile"), dict):
        raise ValueError("Malformed candidate state ledger/profile")
    for source in state["sources"]:
        _verify_source(workspace, source)
    return state


def _verify_source(workspace: Path, source: dict) -> None:
    directory = workspace / "cache/sources" / _source_id(source["source_id"])
    identity = {"fingerprint": source["fingerprint"], "source_type": source["source_type"]}
    if source.get("source_type") == "candidate_response":
        identity["event_id"] = _text(source.get("event_id"), "answer event_id")
    if source.get("source_type") not in {"document", "candidate_response"} or source[
        "source_id"
    ] != _hash(identity):
        raise ValueError("Source metadata mutation detected")
    if source.get("original_path") != str(directory / "original") or source.get(
        "blocks_path"
    ) != str(directory / "blocks.json"):
        raise ValueError("Source path mutation detected")
    for name, key in (("original", "fingerprint"), ("blocks.json", "blocks_fingerprint")):
        path = directory / name
        _safe(path)
        if not path.is_file() or _file_hash(path) != source[key]:
            raise ValueError(f"Source mutation detected: {path}")


def _context(state: dict) -> dict:
    result = copy.deepcopy(state)
    suspended = {
        claim_id
        for conflict in state["ledger"]["conflicts"]
        if conflict["status"] == "unresolved"
        for claim_id in conflict["claim_ids"]
    }
    claims = {c["claim_id"]: c for e in state["ledger"]["entities"] for c in e["claims"]}
    active_entities = {
        e["entity_id"] for e in state["ledger"]["entities"] if e.get("state") == "active"
    }
    eligible = {
        c["claim_id"]
        for e in state["ledger"]["entities"]
        if e["entity_id"] in active_entities
        for c in e["claims"]
        if c.get("evidence_state") in {"sourced", "candidate_confirmed"}
    }
    active = sorted(
        key
        for key, claim in claims.items()
        if claim["status"] == "active"
        and claim["polarity"] == "positive"
        and key in eligible
        and key not in suspended
    )
    name_id = state["profile"]["display_name_claim_id"]
    result.update(
        context_id="sha256:" + _hash(state),
        active_claim_ids=active,
        display_name=claims[name_id]["claim_text"] if name_id in active else None,
    )
    return result


def load_candidate_context(workspace: Path) -> dict:
    return _context(_state(validate_workspace(workspace)))


def _source_id(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("Invalid source_id; expected SHA-256 identifier")
    return value


def prepare_import(
    workspace: Path,
    input_path: Path,
    *,
    source_type: str = "document",
    event_id: str | None = None,
) -> dict:
    if source_type not in {"document", "candidate_response"}:
        raise ValueError("source_type must be document or candidate_response")
    if event_id is not None and source_type != "candidate_response":
        raise ValueError("event_id is only valid for candidate_response")
    if source_type == "candidate_response":
        event_id = str(uuid.uuid4()) if event_id is None else _text(event_id, "event_id")
    input_path = Path(input_path).expanduser().resolve()
    if source_type == "candidate_response" and input_path.suffix.casefold() != ".txt":
        raise ValueError("candidate_response requires a .txt source")
    with workspace_lock(workspace) as workspace:
        context = load_candidate_context(workspace)
        data = input_path.read_bytes()
        fingerprint = hashlib.sha256(data).hexdigest()
        identity = {"fingerprint": fingerprint, "source_type": source_type}
        if source_type == "candidate_response":
            identity["event_id"] = event_id
        source_id = _hash(identity)
        existing = next((s for s in context["sources"] if s["source_id"] == source_id), None)
        if existing:
            return {
                **existing,
                "status": "unchanged",
                "context_id": context["context_id"],
                "blocks": _read(Path(existing["blocks_path"]))["blocks"],
            }
        directory = workspace / "cache/sources" / source_id
        _safe(directory)
        directory.mkdir(parents=True, exist_ok=True)
        original = directory / "original"
        _safe(original)
        if original.exists():
            if _file_hash(original) != fingerprint:
                raise ValueError("Source mutation detected in pending original")
        else:
            with original.open("xb") as stream:
                stream.write(data)
        # Extract the saved bytes, not a mutable caller path.
        descriptor, temp = tempfile.mkstemp(suffix=input_path.suffix, dir=directory)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
            blocks = extract_resume_blocks(Path(temp))
        finally:
            os.unlink(temp)
        block_path = directory / "blocks.json"
        if block_path.exists():
            if _read(block_path) != {"blocks": blocks}:
                raise ValueError("Source mutation or changed extraction detected")
        else:
            _write(block_path, {"blocks": blocks})
        record = {
            "source_id": source_id,
            "source_type": source_type,
            "fingerprint": fingerprint,
            "blocks_fingerprint": _file_hash(block_path),
            "original_path": str(original),
            "blocks_path": str(block_path),
            "context_id": context["context_id"],
            "blocks": blocks,
            "status": "prepared",
        }
        if event_id is not None:
            record["event_id"] = event_id
        _write(workspace / "cache/imports" / f"{source_id}.json", record)
        return record


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} requires nonempty text")
    return value


def _provenance(raw: dict, source: dict) -> dict:
    ids = raw.get("block_ids")
    blocks = {b["block_id"]: b for b in source["blocks"]}
    if (
        not isinstance(ids, list)
        or not ids
        or any(not isinstance(i, str) or i not in blocks for i in ids)
    ):
        raise ValueError("Unknown or missing source block_ids")
    excerpt = _text(raw.get("original_excerpt"), "original_excerpt")
    if excerpt not in "\n".join(blocks[i]["text"] for i in ids):
        raise ValueError("original_excerpt does not exist in selected source blocks")
    return {
        "source_id": source["source_id"],
        "source_type": source["source_type"],
        "block_ids": ids,
        "locations": [blocks[i]["location"] for i in ids],
        "original_excerpt": excerpt,
    }


def commit_import(workspace: Path, source_id: str, proposal: dict) -> dict:
    source_id = _source_id(source_id)
    if not isinstance(proposal, dict):
        raise ValueError("Proposal must be an object")
    for key in (
        "entities",
        "claims",
        "relationships",
        "revoke_relationships",
        "conflicts",
        "resolve_conflicts",
    ):
        records = proposal.get(key, [])
        if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
            raise ValueError(f"Proposal {key} must be an array of objects")
        for raw in records:
            if "reactivate" in raw and type(raw["reactivate"]) is not bool:
                raise ValueError("reactivate must be a boolean")
            for name in ("entity_id", "entity_ref", "project_ref", "employment_ref", "conflict_id"):
                if name in raw:
                    _text(raw[name], name)
            for name in ("supersedes", "claim_refs", "selected_claim_ids"):
                if name in raw and (
                    not isinstance(raw[name], list)
                    or any(not isinstance(item, str) for item in raw[name])
                ):
                    raise ValueError(f"{name} must be an array of string IDs/references")
    if proposal.get("candidate_id") is not None:
        _text(proposal["candidate_id"], "candidate_id")
    if proposal.get("display_name_ref") is not None:
        _text(proposal["display_name_ref"], "display_name_ref")
    with workspace_lock(workspace) as workspace:
        state = _state(workspace)
        context = _context(state)
        state_path = workspace / "cache/candidate-state.json"
        if any(s["source_id"] == source_id for s in state["sources"]):
            return {
                "status": "unchanged",
                "source_id": source_id,
                "context_id": context["context_id"],
                "state_path": str(state_path),
            }
        source = _read(workspace / "cache/imports" / f"{source_id}.json")
        if source.get("source_id") != source_id:
            raise ValueError("Pending source_id mutation detected")
        _verify_source(workspace, source)
        if source.get("blocks") != _read(Path(source["blocks_path"]))["blocks"]:
            raise ValueError("Pending source blocks mutation detected")
        if (
            proposal.get("context_id") != source["context_id"]
            or source["context_id"] != context["context_id"]
        ):
            raise ValueError("Import context is stale; prepare again against current context")
        explicit_candidate = proposal.get("candidate_id")
        if explicit_candidate and explicit_candidate != state["candidate_id"]:
            raise ValueError("Identity conflict: candidate_id does not match workspace")
        ledger = state["ledger"]
        entities = {e["entity_id"]: e for e in ledger["entities"]}
        entity_refs: dict[str, dict] = {}
        claims = {c["claim_id"]: (e, c) for e in entities.values() for c in e["claims"]}
        claim_refs: dict[str, str] = {}
        counts = {
            "new_entities": 0,
            "existing_entities": 0,
            "new_claims": 0,
            "existing_claims": 0,
            "superseded_claims": 0,
            "new_relationships": 0,
            "existing_relationships": 0,
            "retained_claims": len(claims),
        }
        for raw in proposal.get("entities", []):
            ref = _text(raw.get("ref"), "entity ref")
            kind = raw.get("entity_type")
            if ref in entity_refs or not isinstance(kind, str) or kind not in ENTITY_TYPES:
                raise ValueError("Duplicate entity ref or invalid entity_type")
            entity_id = raw.get("entity_id")
            if entity_id:
                if entity_id not in entities or entities[entity_id]["entity_type"] != kind:
                    raise ValueError("Unknown entity_id or mismatched entity_type")
                entity = entities[entity_id]
                counts["existing_entities"] += 1
            else:
                entity = {
                    "entity_id": str(uuid.uuid4()),
                    "entity_type": kind,
                    "label": _text(raw.get("label"), "entity label"),
                    "state": "active",
                    "claims": [],
                }
                ledger["entities"].append(entity)
                entities[entity["entity_id"]] = entity
                counts["new_entities"] += 1
            entity_refs[ref] = entity
        for raw in proposal.get("claims", []):
            ref = _text(raw.get("ref"), "claim ref")
            if ref in claim_refs or ref in claims:
                raise ValueError("Duplicate claim ref")
            entity = entity_refs.get(raw.get("entity_ref")) or entities.get(raw.get("entity_ref"))
            if entity is None:
                raise ValueError("Unknown claim entity_ref")
            text = _text(raw.get("claim_text"), "claim_text")
            provenance = _provenance(raw, source)
            polarity = raw.get("polarity", "positive")
            if not isinstance(polarity, str) or polarity not in {"positive", "negative"}:
                raise ValueError("Invalid polarity")
            field = raw.get("field")
            if field is not None:
                _text(field, "field")
            supersedes = raw.get("supersedes", [])
            if not isinstance(supersedes, list):
                raise ValueError("supersedes must be an array")
            for old_id in supersedes:
                if old_id not in claims or claims[old_id][0]["entity_id"] != entity["entity_id"]:
                    raise ValueError(
                        "supersedes must reference an existing claim on the same entity"
                    )
            if entity["entity_type"] == "profile" and field == "name" and polarity == "positive":
                previous_names = [
                    c
                    for e in entities.values()
                    if e["entity_type"] == "profile"
                    for c in e["claims"]
                    if c.get("field") == "name"
                    and c["status"] == "active"
                    and c["polarity"] == "positive"
                ]
                if (
                    any(
                        c["claim_text"] != text and c["claim_id"] not in supersedes
                        for c in previous_names
                    )
                    and not explicit_candidate
                ):
                    raise ValueError(
                        "Identity conflict: explicitly associate candidate_id or correct name"
                    )
            existing = next(
                (
                    c
                    for c in entity["claims"]
                    if c["claim_text"] == text
                    and c.get("field") == field
                    and c["polarity"] == polarity
                ),
                None,
            )
            if existing:
                claim = existing
                if raw.get("reactivate") is True and claim["status"] != "active":
                    claim["history"].append(
                        {
                            "action": "reactivated",
                            "previous_status": claim["status"],
                            "source_id": source_id,
                            "provenance": provenance,
                        }
                    )
                    claim["status"] = "active"
                if provenance not in claim["provenance"]:
                    claim["provenance"].append(provenance)
                counts["existing_claims"] += 1
            else:
                claim = {
                    "claim_id": str(uuid.uuid4()),
                    "claim_text": text,
                    "field": field,
                    "polarity": polarity,
                    "status": "active",
                    "provenance": [provenance],
                    "evidence_state": "candidate_confirmed"
                    if source["source_type"] == "candidate_response"
                    else "sourced",
                    "supersedes": [],
                    "history": [],
                }
                entity["claims"].append(claim)
                counts["new_claims"] += 1
            if claim["claim_id"] in supersedes:
                raise ValueError("A claim cannot supersede itself")
            if source["source_type"] == "candidate_response":
                claim["evidence_state"] = "candidate_confirmed"
            for old_id in supersedes:
                old = claims[old_id][1]
                old["status"] = "superseded"
                old["history"].append({"superseded_by": claim["claim_id"], "source_id": source_id})
                if old_id not in claim["supersedes"]:
                    claim["supersedes"].append(old_id)
                counts["superseded_claims"] += 1
            claims[claim["claim_id"]] = (entity, claim)
            claim_refs[ref] = claim["claim_id"]
        for raw in proposal.get("relationships", []):
            project = entity_refs.get(raw.get("project_ref")) or entities.get(
                raw.get("project_ref")
            )
            employment = entity_refs.get(raw.get("employment_ref")) or entities.get(
                raw.get("employment_ref")
            )
            if (
                not project
                or not employment
                or project["entity_type"] != "project"
                or employment["entity_type"] != "employment"
            ):
                raise ValueError("Relationship must link project to employment")
            provenance = _provenance(raw, source)
            supersedes = raw.get("supersedes", [])
            previous_relations = {
                relation["relationship_id"]: relation for relation in ledger["relationships"]
            }
            for old_id in supersedes:
                if old_id not in previous_relations or (
                    previous_relations[old_id]["project_id"] != project["entity_id"]
                ):
                    raise ValueError("Relationship supersedes must reference the same project")
            existing = next(
                (
                    r
                    for r in ledger["relationships"]
                    if r["project_id"] == project["entity_id"]
                    and r["employment_id"] == employment["entity_id"]
                ),
                None,
            )
            if existing:
                if raw.get("reactivate") is True and existing["state"] != "active":
                    existing.setdefault("history", []).append(
                        {
                            "action": "reactivated",
                            "previous_state": existing["state"],
                            "provenance": provenance,
                        }
                    )
                    existing["state"] = "active"
                if provenance not in existing["provenance"]:
                    existing["provenance"].append(provenance)
                counts["existing_relationships"] += 1
            else:
                existing = {
                    "relationship_id": str(uuid.uuid4()),
                    "project_id": project["entity_id"],
                    "employment_id": employment["entity_id"],
                    "state": "active",
                    "provenance": [provenance],
                    "history": [],
                }
                ledger["relationships"].append(existing)
                counts["new_relationships"] += 1
            for old_id in supersedes:
                if old_id == existing["relationship_id"]:
                    raise ValueError("A relationship cannot supersede itself")
                previous = previous_relations[old_id]
                previous["state"] = "superseded"
                previous.setdefault("history", []).append(
                    {
                        "superseded_by": existing["relationship_id"],
                        "provenance": provenance,
                    }
                )
        for raw in proposal.get("revoke_relationships", []):
            relation = next(
                (
                    r
                    for r in ledger["relationships"]
                    if r["relationship_id"] == raw.get("relationship_id")
                ),
                None,
            )
            if relation is None:
                raise ValueError("Unknown relationship_id for revocation")
            provenance = _provenance(raw, source)
            relation["state"] = "revoked"
            relation.setdefault("history", []).append(
                {"action": "revoked", "provenance": provenance}
            )
        for raw in proposal.get("conflicts", []):
            ids = [claim_refs.get(ref, ref) for ref in raw.get("claim_refs", [])]
            if len(set(ids)) < 2 or any(i not in claims for i in ids):
                raise ValueError("Conflict requires at least two known claims")
            resolved = next(
                (
                    c
                    for c in ledger["conflicts"]
                    if c["status"] == "resolved" and set(c["claim_ids"]) == set(ids)
                ),
                None,
            )
            if resolved:
                resolved["history"].append(
                    {
                        "source_id": source_id,
                        "status": "resolved",
                        "reason": "Repeated historical conflict; existing resolution retained",
                    }
                )
                resolved["version"] += 1
                continue
            if any(old in claims[new][1].get("supersedes", []) for old in ids for new in ids):
                continue
            ledger["conflicts"].append(
                {
                    "conflict_id": str(uuid.uuid4()),
                    "claim_ids": ids,
                    "reason": _text(raw.get("reason"), "conflict reason"),
                    "status": "unresolved",
                    "version": 1,
                    "history": [],
                    "source_id": source_id,
                }
            )
        for raw in proposal.get("resolve_conflicts", []):
            conflict = next(
                (c for c in ledger["conflicts"] if c["conflict_id"] == raw.get("conflict_id")), None
            )
            if conflict is None or conflict["status"] != "unresolved":
                raise ValueError("Unknown or already resolved conflict")
            provenance = _provenance(raw, source)
            selected = [claim_refs.get(i, i) for i in raw.get("selected_claim_ids", [])]
            if not selected or not set(selected) <= set(conflict["claim_ids"]):
                raise ValueError("Resolution must select conflicting claims")
            conflict["history"].append({"version": conflict["version"], "status": "unresolved"})
            conflict.update(
                status="resolved",
                version=conflict["version"] + 1,
                selected_claim_ids=selected,
                resolution_provenance=provenance,
            )
            for claim_id in conflict["claim_ids"]:
                if claim_id not in selected:
                    claims[claim_id][1]["status"] = "revoked"
                    claims[claim_id][1]["history"].append(
                        {
                            "conflict_id": conflict["conflict_id"],
                            "source_id": source_id,
                            "status": "revoked",
                        }
                    )
        preferences = proposal.get("preferences", {})
        if not isinstance(preferences, dict):
            raise ValueError("preferences must be an object")
        state["profile"]["preferences"].update(preferences)
        if proposal.get("display_name_ref") is not None:
            name_id = claim_refs.get(proposal["display_name_ref"], proposal["display_name_ref"])
            if (
                name_id not in claims
                or claims[name_id][0]["entity_type"] != "profile"
                or claims[name_id][1].get("field") != "name"
                or claims[name_id][1]["polarity"] != "positive"
                or claims[name_id][1]["status"] != "active"
            ):
                raise ValueError(
                    "display_name_ref must select an active positive profile name claim"
                )
            state["profile"]["display_name_claim_id"] = name_id
        state["candidate_id"] = state["candidate_id"] or str(uuid.uuid4())
        state["sources"].append(
            {k: v for k, v in source.items() if k not in {"blocks", "status", "context_id"}}
        )
        # History is staged before the only authoritative commit point.
        if state_path.exists():
            history_name = context["context_id"].replace(":", "-") + ".json"
            history = workspace / "cache/state-history" / history_name
            if not history.exists():
                _write(history, _state(workspace))
        _write(state_path, state)
        final = _context(state)
        unresolved = [c for c in ledger["conflicts"] if c["status"] == "unresolved"]
        active_new = set(claim_refs.values()) & set(final["active_claim_ids"])
        provenances = [p for _, c in claims.values() for p in c["provenance"]]
        provenances.extend(p for r in ledger["relationships"] for p in r["provenance"])
        provenances.extend(
            h["provenance"]
            for r in ledger["relationships"]
            for h in r.get("history", [])
            if "provenance" in h
        )
        provenances.extend(
            c["resolution_provenance"] for c in ledger["conflicts"] if "resolution_provenance" in c
        )
        used_blocks = {
            b for p in provenances if p["source_id"] == source_id for b in p["block_ids"]
        }
        status = (
            "partial"
            if unresolved and active_new
            else "needs_clarification"
            if unresolved
            else "committed"
        )
        return {
            "status": status,
            "source_id": source_id,
            "context_id": final["context_id"],
            "candidate_id": state["candidate_id"],
            "state_path": str(state_path),
            "original_path": source["original_path"],
            "blocks_path": source["blocks_path"],
            "counts": counts,
            "entity_ids": {ref: e["entity_id"] for ref, e in entity_refs.items()},
            "claim_ids": dict(claim_refs),
            "conflicts": unresolved,
            "unparsed_blocks": [b for b in source["blocks"] if b["block_id"] not in used_blocks],
        }
