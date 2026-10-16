"""File transaction behavior with synthetic artifacts, without rendering or review claims."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from scripts.accepted_resume_publication import commit_accepted_resume
from scripts.resume_history_manager import read_records


class AcceptedResumePublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name).resolve()
        self.pdf = self.workspace / "candidate.pdf"
        self.pdf.write_bytes(b"synthetic candidate PDF")
        self.pdf.with_suffix(".docx").write_bytes(b"synthetic candidate DOCX")
        self.record = {
            "target": {"company": "Example", "role": "Engineer", "job_url": ""},
            "pdf_sha256": hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
            "docx_sha256": hashlib.sha256(self.pdf.with_suffix(".docx").read_bytes()).hexdigest(),
        }
        self.review = {"purpose": "synthetic file transaction fixture, not actual review"}

    def commit(self, output_format: str = "both") -> dict[str, Any]:
        return commit_accepted_resume(
            self.workspace, self.pdf, self.record, self.review,
            output_name="target.docx", output_format=output_format,
        )

    def snapshot(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.workspace)): path.read_bytes()
            for name in ("resume_output", "resume_history")
            for path in (self.workspace / name).rglob("*")
            if path.is_file()
        }

    def seed_previous(self) -> dict[str, bytes]:
        self.commit()
        for ext in (".pdf", ".docx"):
            (self.workspace / "resume_output" / ("target" + ext)).write_bytes(
                b"previous accepted " + ext.encode("ascii")
            )
        return self.snapshot()

    def assert_clean(self) -> None:
        self.assertFalse(list(self.workspace.glob(".publication-*")))
        self.assertFalse((self.workspace / "resume_history/.lock").exists())
        self.assertEqual(self.pdf.read_bytes(), b"synthetic candidate PDF")
        self.assertEqual(self.pdf.with_suffix(".docx").read_bytes(), b"synthetic candidate DOCX")

    def test_formats_save_complete_history_and_retire_old_counterpart(self) -> None:
        for output_format in ("both", "docx", "pdf"):
            with self.subTest(output_format=output_format):
                result = self.commit(output_format)
                extensions = (".docx", ".pdf") if output_format == "both" else ("." + output_format,)
                self.assertEqual(
                    result["outputs"],
                    [str(self.workspace / "resume_output" / ("target" + ext)) for ext in extensions],
                )
                for ext in (".pdf", ".docx"):
                    output = self.workspace / "resume_output" / ("target" + ext)
                    self.assertEqual(output.exists(), ext in extensions)
                    if output.exists():
                        self.assertEqual(output.read_bytes(), self.pdf.with_suffix(ext).read_bytes())
                historical = Path(result["historical_pdf"])
                self.assertEqual(historical.read_bytes(), self.pdf.read_bytes())
                self.assertEqual(historical.stat().st_mode & 0o222, 0)
                self.assertEqual(
                    json.loads((historical.parent / "review.json").read_text(encoding="utf-8")),
                    self.review,
                )
                self.assertEqual(
                    json.loads((historical.parent / "candidate-record.json").read_text(encoding="utf-8")),
                    self.record,
                )
                self.assertIn(
                    historical.parent.name, Path(result["history_index"]).read_text(encoding="utf-8")
                )
                self.assert_clean()
        self.assertEqual(len(read_records(self.workspace / "resume_history")), 3)

    def test_every_commit_move_failure_restores_previous_files(self) -> None:
        original = Path.replace
        before = self.seed_previous()
        # Two backups, two outputs, history, previous index, new index.
        for fail_at in range(1, 8):
            calls = 0

            def fail_one(source: Path, destination: Path) -> Path:
                nonlocal calls
                calls += 1
                if calls == fail_at:
                    raise OSError("injected transaction failure")
                return original(source, destination)

            with self.subTest(fail_at=fail_at), patch.object(Path, "replace", fail_one):
                with self.assertRaisesRegex(OSError, "injected transaction"):
                    self.commit()
            self.assertGreaterEqual(calls, fail_at)
            self.assertEqual(self.snapshot(), before)
            self.assert_clean()

    def test_first_publication_failure_leaves_no_output_or_history_files(self) -> None:
        original = Path.replace

        def fail_index(source: Path, destination: Path) -> Path:
            if destination == self.workspace / "resume_history/index.html":
                raise OSError("index install failed")
            return original(source, destination)

        with patch.object(Path, "replace", fail_index):
            with self.assertRaisesRegex(OSError, "index install"):
                self.commit()
        self.assertEqual(self.snapshot(), {})
        self.assert_clean()

    def test_preparation_failures_leave_previous_files_untouched(self) -> None:
        before = self.seed_previous()
        copy = shutil.copyfile
        open_file = Path.open
        for filename in ("resume.pdf", "resume.docx", "record.json", "review.json", "candidate-record.json", "index.html"):
            fired = False

            def fail_copy(source: Path, destination: Path) -> str:
                nonlocal fired
                if destination.name == filename:
                    fired = True
                    raise OSError("staging failed")
                return copy(source, destination)

            def fail_open(source: Path, *args: Any, **kwargs: Any) -> Any:
                nonlocal fired
                mode = args[0] if args else kwargs.get("mode")
                if source.name == filename and mode in ("x", "w"):
                    fired = True
                    raise OSError("staging failed")
                return open_file(source, *args, **kwargs)

            with self.subTest(filename=filename), patch(
                "scripts.accepted_resume_publication.shutil.copyfile", fail_copy
            ), patch.object(Path, "open", fail_open):
                with self.assertRaisesRegex(OSError, "staging failed"):
                    self.commit()
            self.assertTrue(fired)
            self.assertEqual(self.snapshot(), before)
            self.assert_clean()

    def test_changed_staged_bytes_are_rejected(self) -> None:
        before = self.seed_previous()
        copy = shutil.copyfile

        def mutate_copy(source: Path, destination: Path) -> str:
            result = copy(source, destination)
            if destination.name == "resume.docx":
                destination.write_bytes(b"changed during staging")
            return result

        with patch("scripts.accepted_resume_publication.shutil.copyfile", mutate_copy):
            with self.assertRaisesRegex(ValueError, "changed during publication staging"):
                self.commit()
        self.assertEqual(self.snapshot(), before)
        self.assert_clean()

    def test_failed_rollback_retains_recovery_files_and_attempts_other_restores(self) -> None:
        before = self.seed_previous()
        previous_index = (self.workspace / "resume_history/index.html").read_bytes()
        original = Path.replace
        failures = 0

        def fail_index_and_restore(source: Path, destination: Path) -> Path:
            nonlocal failures
            if destination == self.workspace / "resume_history/index.html":
                failures += 1
                raise OSError("index unavailable")
            return original(source, destination)

        with patch.object(Path, "replace", fail_index_and_restore):
            with self.assertRaisesRegex(RuntimeError, "recovery files retained"):
                self.commit()
        self.assertEqual(failures, 2)
        stage = next(self.workspace.glob(".publication-*"))
        self.assertEqual((stage / "previous-index.html").read_bytes(), previous_index)
        self.assertEqual(len(read_records(self.workspace / "resume_history")), 1)
        for ext in (".pdf", ".docx"):
            self.assertEqual(
                (self.workspace / "resume_output" / ("target" + ext)).read_bytes(),
                before["resume_output/target" + ext],
            )
        self.assertFalse((self.workspace / "resume_history/.lock").exists())

    def test_existing_backups_and_unrelated_outputs_are_preserved(self) -> None:
        before = self.seed_previous()
        backup_dir = self.workspace / "resume_output/backup/Uncategorized"
        backup_dir.mkdir(parents=True)
        older = backup_dir / "target_old_1.docx"
        older.write_bytes(b"older accepted DOCX")
        unrelated = self.workspace / "resume_output/unrelated.docx"
        unrelated.write_bytes(b"another target")
        self.commit("docx")
        self.assertEqual(older.read_bytes(), b"older accepted DOCX")
        self.assertEqual(
            (backup_dir / "target_old_2.docx").read_bytes(), before["resume_output/target.docx"]
        )
        self.assertEqual(
            (backup_dir / "target_old_1.pdf").read_bytes(), before["resume_output/target.pdf"]
        )
        self.assertEqual(unrelated.read_bytes(), b"another target")
        self.assert_clean()

    def test_invalid_history_index_is_rejected_before_output_changes(self) -> None:
        before = self.seed_previous()
        index = self.workspace / "resume_history/index.html"
        index.unlink()
        index.mkdir()
        with self.assertRaisesRegex(ValueError, "History index must be a regular file"):
            self.commit()
        for ext in (".pdf", ".docx"):
            self.assertEqual(
                (self.workspace / "resume_output" / ("target" + ext)).read_bytes(),
                before["resume_output/target" + ext],
            )
        self.assertEqual(len(read_records(index.parent)), 1)
        self.assert_clean()


if __name__ == "__main__":
    unittest.main()
