from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import resume_history_manager as history


class ResumeHistoryManagerTests(unittest.TestCase):
    def test_repeated_records_keep_stable_pdf_links_and_url_backfill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            pdf = workspace / "candidate.pdf"
            pdf.write_bytes(b"first")
            with history.register_generation(workspace, pdf, '<script>&"', "Engineer", "") as first:
                pass
            pdf.write_bytes(b"second")
            with history.register_generation(workspace, pdf, "Same", "Engineer", "") as second:
                pass
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

    def test_publication_failure_restores_index_and_removes_new_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            pdf = workspace / "candidate.pdf"
            pdf.write_bytes(b"accepted")
            with history.register_generation(workspace, pdf, "", "", ""):
                pass
            root = history.history_path(workspace)
            before = (root / "index.html").read_bytes()
            with self.assertRaisesRegex(OSError, "publication"):
                with history.register_generation(workspace, pdf, "", "", ""):
                    raise OSError("publication failed")
            self.assertEqual((root / "index.html").read_bytes(), before)
            self.assertEqual(len(history.read_records(root)), 1)
            self.assertFalse((root / ".lock").exists())

    def test_copy_or_index_failure_does_not_leave_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            pdf = workspace / "candidate.pdf"
            pdf.write_bytes(b"candidate")
            for target in ("shutil.copyfile", "atomic_text"):
                with self.subTest(target=target):
                    with mock.patch(
                        f"scripts.resume_history_manager.{target}", side_effect=OSError("disk")
                    ):
                        with self.assertRaises(OSError):
                            with history.register_generation(workspace, pdf, "", "", ""):
                                self.fail("must not publish")
                    self.assertEqual(history.read_records(history.history_path(workspace)), [])

    def test_url_update_index_failure_restores_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            pdf = workspace / "candidate.pdf"
            pdf.write_bytes(b"candidate")
            with history.register_generation(workspace, pdf, "", "", "") as archived:
                pass
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
