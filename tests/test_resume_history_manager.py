from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import resume_history_manager as history
from scripts.accepted_resume_publication import commit_accepted_resume


class ResumeHistoryManagerTests(unittest.TestCase):
    def publish(
        self, workspace: Path, pdf: Path, company: str = "", role: str = ""
    ) -> Path:
        docx = pdf.with_suffix(".docx")
        docx.write_bytes(b"synthetic DOCX")
        record = {
            "target": {"company": company, "role": role},
            "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "docx_sha256": hashlib.sha256(docx.read_bytes()).hexdigest(),
        }
        result = commit_accepted_resume(
            workspace, pdf, record, {"purpose": "synthetic transaction fixture"},
            output_name="resume.docx", output_format="docx",
        )
        return Path(result["historical_pdf"])

    def test_repeated_records_keep_stable_pdf_links_and_url_backfill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            pdf = workspace / "candidate.pdf"
            pdf.write_bytes(b"first")
            first = self.publish(workspace, pdf, '<script>&"', "Engineer")
            pdf.write_bytes(b"second")
            second = self.publish(workspace, pdf, "Same", "Engineer")
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_bytes(), b"first")
            previous = json.loads((first.parent / "record.json").read_text())
            history.update_job_url(workspace, first.parent.name, "https://example.org/jobs?a=1&b=2")
            current = json.loads((first.parent / "record.json").read_text())
            self.assertEqual(
                {k: v for k, v in previous.items() if k != "job_url"},
                {k: v for k, v in current.items() if k != "job_url"},
            )
            html = (history.history_path(workspace) / "index.html").read_text()
            self.assertIn("&lt;script&gt;&amp;&quot;", html)
            self.assertNotIn("<script>", html)
            self.assertIn(first.relative_to(history.history_path(workspace)).as_posix(), html)
            self.assertEqual(len(history.read_records(history.history_path(workspace))), 2)

    def test_unsafe_urls_and_workspace_symlinks_rejected(self) -> None:
        for value in (
            "javascript:alert(1)",
            "file:///tmp/a",
            "//example.org",
            "https://",
            "https://user:password@example.org",
            "https://example.org/\nx",
            "https://example.org\\evil",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                history.validate_job_url(value)
        with self.assertRaises(ValueError):
            history.history_path(history.PROJECT_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "resume_history").symlink_to(
                history.PROJECT_ROOT, target_is_directory=True
            )
            with self.assertRaises(ValueError):
                history.history_path(workspace)

    def test_url_update_index_failure_restores_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            pdf = workspace / "candidate.pdf"
            pdf.write_bytes(b"candidate")
            archived = self.publish(workspace, pdf)
            original = history.atomic_text

            def fail_index(path: Path, text: str) -> None:
                if path.name == "index.html":
                    raise OSError("index failed")
                original(path, text)

            with mock.patch.object(history, "atomic_text", side_effect=fail_index):
                with self.assertRaises(OSError):
                    history.update_job_url(
                        workspace, archived.parent.name, "https://example.org/job"
                    )
            self.assertEqual(history.read_records(archived.parent.parent)[0]["job_url"], "")

    def test_corrupt_record_and_busy_history_lock_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = history.history_path(Path(directory))
            with history.history_lock(root):
                with self.assertRaisesRegex(ValueError, "busy"):
                    with history.history_lock(root):
                        self.fail("must not acquire twice")
            malformed = root / ("generation-" + "a" * 32)
            malformed.mkdir()
            (malformed / "record.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid Resume"):
                history.read_records(root)


if __name__ == "__main__":
    unittest.main()
