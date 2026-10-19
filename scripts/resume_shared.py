#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared utilities for resume scripts: validation, JSON I/O, parsing helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterator

REQUIRED_KEYS = ("name", "contact", "skills", "experience", "education")
DEFAULT_WORKSPACE_REL_PATH = Path("Documents") / "MonkeyResume"


def default_user_workspace() -> Path:
    """Return the default candidate workspace outside the Skill package."""
    return Path.home() / DEFAULT_WORKSPACE_REL_PATH


def add_workspace_argument(parser: argparse.ArgumentParser) -> None:
    """Add the shared optional candidate-workspace argument to a CLI parser."""
    parser.add_argument(
        "--workspace",
        type=Path,
        default=default_user_workspace(),
        help="Candidate workspace root (default: ~/Documents/MonkeyResume)",
    )


def resolve_user_workspace(workspace: Path) -> Path:
    """Expand and resolve a candidate workspace supplied by argparse."""
    return workspace.expanduser().resolve()


ACTION_VERBS: frozenset[str] = frozenset(
    {
        "accelerated",
        "achieved",
        "automated",
        "built",
        "created",
        "delivered",
        "designed",
        "developed",
        "directed",
        "drove",
        "enabled",
        "engineered",
        "established",
        "executed",
        "expanded",
        "generated",
        "grew",
        "headed",
        "identified",
        "implemented",
        "improved",
        "increased",
        "initiated",
        "integrated",
        "introduced",
        "launched",
        "led",
        "managed",
        "migrated",
        "modernized",
        "optimized",
        "orchestrated",
        "overhauled",
        "pioneered",
        "proposed",
        "reduced",
        "redesigned",
        "refactored",
        "resolved",
        "revamped",
        "scaled",
        "secured",
        "simplified",
        "spearheaded",
        "standardized",
        "streamlined",
        "strengthened",
        "supervised",
        "transformed",
        "unified",
        "upgraded",
    }
)
_ACTION_VERB_RE = re.compile(
    rf"^(?:{'|'.join(sorted(map(re.escape, ACTION_VERBS), key=len, reverse=True))})\b",
    re.IGNORECASE,
)
_SKILL_REQUIRED = ("category", "items")
_EXPERIENCE_REQUIRED = ("company", "title", "dates", "bullets")
_EDUCATION_REQUIRED = ("school", "degree", "dates")


def normalize_skill_items(value: Any) -> list[str]:
    """Validate and normalize the current array-of-strings skills format."""
    if not isinstance(value, list):
        raise ValueError("Skill items must be an array of strings.")
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"Skill item at index {index} must be a non-empty string.")
        items.append(item.strip())
    return items


def validate_resume_content(payload: dict[str, Any], *, require_non_empty: bool = False) -> None:
    """Validate resume JSON has required keys and correct types.

    When *require_non_empty* is True, required fields must also be non-empty.
    """
    if "summary" in payload:
        raise ValueError(
            "`summary` is no longer a supported resume field. "
            "Place relevant, supported contributions in experience or skills instead."
        )
    missing = [key for key in REQUIRED_KEYS if key not in payload]
    if missing:
        raise ValueError(f"Input content missing required fields: {', '.join(missing)}")

    if "project_heading" in payload:
        if payload["project_heading"] not in ("Projects", "Open Source Projects"):
            raise ValueError("`project_heading` must be Projects or Open Source Projects.")
        if not payload.get("projects"):
            raise ValueError("`project_heading` requires a non-empty projects section.")

    for key in ("name", "contact"):
        value = payload[key]
        if not isinstance(value, str):
            raise ValueError(f"`{key}` must be a string.")
        if require_non_empty and not value.strip():
            raise ValueError(f"`{key}` must be non-empty.")

    for key in ("skills", "experience", "education"):
        value = payload[key]
        if not isinstance(value, list):
            raise ValueError(f"`{key}` must be an array.")
        if require_non_empty and not value:
            raise ValueError(f"`{key}` must be a non-empty array.")

    # -- Nested field validation for skills --
    for i, entry in enumerate(payload["skills"]):
        if not isinstance(entry, dict):
            raise ValueError(f"skills[{i}] must be an object")
        for field in _SKILL_REQUIRED:
            if field not in entry:
                raise ValueError(f"skills[{i}] missing required field: {field}")
        if not isinstance(entry["category"], str):
            raise ValueError(f"skills[{i}].category must be a str")
        items_value = entry["items"]
        if not isinstance(items_value, list):
            raise ValueError(f"skills[{i}].items must be an array of strings")
        normalized = normalize_skill_items(items_value)
        if not normalized:
            raise ValueError(f"skills[{i}].items must not be an empty array.")

    # -- Nested field validation for experience --
    for i, entry in enumerate(payload["experience"]):
        if not isinstance(entry, dict):
            raise ValueError(f"experience[{i}] must be an object")
        for field in _EXPERIENCE_REQUIRED:
            if field not in entry:
                raise ValueError(f"experience[{i}] missing required field: {field}")
        for field in ("company", "title", "dates"):
            if not isinstance(entry[field], str):
                raise ValueError(f"experience[{i}].{field} must be a str")
        if "location" in entry and not isinstance(entry["location"], str):
            raise ValueError(f"experience[{i}].location must be a str")
        if not isinstance(entry["bullets"], list):
            raise ValueError(f"experience[{i}].bullets must be a list")
        for j, bullet in enumerate(entry["bullets"]):
            if not isinstance(bullet, str):
                raise ValueError(f"experience[{i}].bullets[{j}] must be a str")

    # -- Nested field validation for education --
    for i, entry in enumerate(payload["education"]):
        if not isinstance(entry, dict):
            raise ValueError(f"education[{i}] must be an object")
        for field in _EDUCATION_REQUIRED:
            if field not in entry:
                raise ValueError(f"education[{i}] missing required field: {field}")
        if not isinstance(entry["school"], str):
            raise ValueError(f"education[{i}].school must be a str")
        if not isinstance(entry["degree"], str):
            raise ValueError(f"education[{i}].degree must be a str")
        if not isinstance(entry["dates"], str):
            raise ValueError(f"education[{i}].dates must be a str")
        if "location" in entry and not isinstance(entry["location"], str):
            raise ValueError(f"education[{i}].location must be a str")

    optional_specs: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
        "projects": (("name", "bullets"), ("name", "tech", "dates")),
        "certifications": (("name",), ("name", "issuer", "dates")),
        "awards": (("name",), ("name", "organization", "dates")),
    }
    for key, (required_fields, string_fields) in optional_specs.items():
        entries = payload.get(key, [])
        if not isinstance(entries, list):
            raise ValueError(f"`{key}` must be an array when provided.")
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"{key}[{i}] must be an object")
            for field in required_fields:
                if field not in entry:
                    raise ValueError(f"{key}[{i}] missing required field: {field}")
            for field in string_fields:
                if field in entry and not isinstance(entry[field], str):
                    raise ValueError(f"{key}[{i}].{field} must be a str")
            if "bullets" in entry:
                if not isinstance(entry["bullets"], list):
                    raise ValueError(f"{key}[{i}].bullets must be a list")
                for j, bullet in enumerate(entry["bullets"]):
                    if not isinstance(bullet, str):
                        raise ValueError(f"{key}[{i}].bullets[{j}] must be a str")


def load_json_file(path: Path) -> dict[str, Any]:
    """Read a JSON file and return the top-level dict."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"File does not exist: {path}") from None
    if not isinstance(payload, dict):
        raise ValueError(f"JSON must be an object: {path}")
    return payload


def write_json_file(path: Path, payload: dict[str, Any]) -> Path:
    """Atomically write *payload* as pretty-printed UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return path


def canonical_json_fingerprint(payload: dict[str, Any]) -> str:
    """Return a stable SHA-256 fingerprint for a JSON object."""
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def iter_resume_text_fields(
    resume: dict[str, Any],
) -> Iterator[tuple[str, str, str, str]]:
    """Yield substantive display fields as path, text, entity type, and entity key."""
    for field in ("name", "contact"):
        value = resume.get(field)
        if isinstance(value, str) and value.strip():
            yield field, value, "profile", "profile"

    section_specs: dict[str, tuple[str, ...]] = {
        "skills": ("category", "items"),
        "experience": ("company", "title", "location", "dates"),
        "projects": ("name", "tech", "dates"),
        "education": ("school", "degree", "location", "dates"),
        "certifications": ("name", "issuer", "dates"),
        "awards": ("name", "organization", "dates"),
    }
    for section, fields in section_specs.items():
        entries = resume.get(section, [])
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            entity_key = f"{section}[{index}]"
            for field in fields:
                value = entry.get(field)
                if section == "skills" and field == "items":
                    for item_index, item in enumerate(normalize_skill_items(value)):
                        yield f"{entity_key}.items[{item_index}]", item, "skill", entity_key
                    continue
                if isinstance(value, str) and value.strip():
                    yield f"{entity_key}.{field}", value, section.rstrip("s"), entity_key
            bullets = entry.get("bullets", [])
            if isinstance(bullets, list):
                for bullet_index, bullet in enumerate(bullets):
                    if isinstance(bullet, str) and bullet.strip():
                        yield (
                            f"{entity_key}.bullets[{bullet_index}]",
                            bullet,
                            section.rstrip("s"),
                            entity_key,
                        )


def collect_bullets(resume: dict[str, Any]) -> list[str]:
    """Collect experience and project bullets for the current content checks."""
    return [
        bullet
        for section in ("experience", "projects")
        for item in resume.get(section, [])
        for bullet in item.get("bullets", [])
    ]


def term_matches(text: str, term: str) -> bool:
    """Return whether *term* occurs as a boundary-aware phrase in *text*.

    Alphanumeric edges require word boundaries while technical punctuation in
    terms such as ``C++``, ``C#``, and ``.NET`` remains matchable.
    """
    normalized_term = " ".join(term.casefold().split())
    if not normalized_term:
        return False
    normalized_text = " ".join(text.casefold().split())
    left = r"(?<!\w)" if normalized_term[0].isalnum() else ""
    right = r"(?!\w)" if normalized_term[-1].isalnum() else ""
    return bool(re.search(f"{left}{re.escape(normalized_term)}{right}", normalized_text))


def starts_with_action_verb(text: str) -> bool:
    """Return whether *text* opens with a recognized action verb."""
    return bool(_ACTION_VERB_RE.search(text.strip()))
