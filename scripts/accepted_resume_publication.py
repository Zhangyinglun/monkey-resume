"""Commit reviewed Accepted Resume artifacts and history as one file transaction.

The caller holds the workspace lock and verifies current evidence, independent
review and physical QA. This module owns staging, history and output changes,
with one rollback journal. It does not provide recovery after process termination.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from scripts.resume_history_manager import (
    history_lock,
    history_path,
    read_records,
    render_directory,
    validate_job_url,
)
from scripts.resume_shared import resolve_user_workspace


def validate_output_name(name: str) -> str:
    if (
        not isinstance(name, str)
        or Path(name).name != name
        or "\\" in name
        or any(ord(c) < 32 or ord(c) == 127 for c in name)
        or Path(name).suffix.lower() not in {".docx", ".pdf"}
    ):
        raise ValueError("Output must be a safe .docx or .pdf filename, not a path.")
    return name


def _write_json(path: Path, value: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def commit_accepted_resume(
    workspace: Path,
    pdf: Path,
    candidate_record: dict[str, Any],
    review: dict[str, Any],
    *,
    output_name: str,
    output_format: str,
) -> dict[str, Any]:
    """Publish a validated candidate without changing its frozen originals."""
    workspace = resolve_user_workspace(workspace)
    root = history_path(workspace)
    validate_output_name(output_name)
    if output_format not in {"docx", "pdf", "both"}:
        raise ValueError("output_format must be docx, pdf or both.")
    output = workspace / "resume_output"
    backup_dir = output / "backup" / "Uncategorized"
    if output.resolve() != output or backup_dir.resolve() != backup_dir:
        raise ValueError("Publication output and backup directories must not contain symlinks.")
    target = candidate_record["target"]
    job_url = validate_job_url(target.get("job_url", ""))
    extensions = (".docx", ".pdf") if output_format == "both" else ("." + output_format,)
    destinations = {ext: output / Path(output_name).with_suffix(ext) for ext in extensions}
    stage = Path(tempfile.mkdtemp(prefix=".publication-", dir=workspace))
    retain_stage = False
    try:
        # Staged bytes must still match the candidate that passed review.
        for ext in (".pdf", ".docx"):
            source = pdf.with_suffix(ext)
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"Missing or unsafe candidate file: {source}")
            staged = stage / ("resume" + ext)
            shutil.copyfile(source, staged)
            if hashlib.sha256(staged.read_bytes()).hexdigest() != candidate_record[ext[1:] + "_sha256"]:
                raise ValueError("Artifact changed during publication staging.")

        with history_lock(root):
            records = read_records(root)
            record_id = "generation-" + uuid4().hex
            historical = root / record_id
            if historical.exists() or historical.is_symlink():
                raise FileExistsError(f"Resume Generation Record already exists: {historical}")
            index = root / "index.html"
            if index.is_symlink() or (index.exists() and not index.is_file()):
                raise ValueError("History index must be a regular file, not a symlink.")
            metadata = {
                "record_id": record_id,
                "company": target.get("company", "").strip(),
                "job_title": target.get("role", "").strip(),
                "job_url": job_url,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            bundle = stage / record_id
            bundle.mkdir()
            shutil.copyfile(stage / "resume.pdf", bundle / "resume.pdf")
            (bundle / "resume.pdf").chmod(0o444)
            _write_json(bundle / "record.json", metadata)
            _write_json(bundle / "review.json", review)
            _write_json(bundle / "candidate-record.json", candidate_record)
            staged_index = stage / "index.html"
            staged_index.write_text(render_directory([metadata, *records]), encoding="utf-8")

            output.mkdir(parents=True, exist_ok=True)
            archive_targets = [
                path
                for path in output.iterdir()
                if path.stem == Path(output_name).stem
                and path.suffix.casefold() in (".docx", ".pdf")
            ]
            if any(path.is_symlink() for path in archive_targets):
                raise ValueError("Accepted outputs must not be symlinks.")
            journal: list[tuple[Path, Path]] = []

            def move(source: Path, destination: Path) -> None:
                source.replace(destination)
                journal.append((destination, source))

            try:
                for existing in archive_targets:
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    number = 1
                    backup = backup_dir / f"{existing.stem}_old_{number}{existing.suffix}"
                    while backup.exists() or backup.is_symlink():
                        number += 1
                        backup = backup_dir / f"{existing.stem}_old_{number}{existing.suffix}"
                    move(existing, backup)
                for ext in extensions:
                    move(stage / ("resume" + ext), destinations[ext])
                move(bundle, historical)
                if index.exists():
                    move(index, stage / "previous-index.html")
                move(staged_index, index)
            except Exception as error:
                failures = []
                for source, destination in reversed(journal):
                    try:
                        source.replace(destination)
                    except OSError as rollback_error:
                        failures.append(str(rollback_error))
                if failures:
                    retain_stage = True
                    raise RuntimeError(
                        f"Publication rollback incomplete; recovery files retained in {stage}: "
                        + "; ".join(failures)
                    ) from error
                raise
        return {
            "outputs": [str(destinations[ext]) for ext in extensions],
            "historical_pdf": str(historical / "resume.pdf"),
            "history_index": str(index),
        }
    finally:
        if not retain_stage:
            shutil.rmtree(stage, ignore_errors=True)
