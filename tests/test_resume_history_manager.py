from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import resume_history_manager as history
from scripts.resume_cache_manager import reset_cache_on_start
from tests.test_pdf_pipeline import pdfplumber, prepare_audited_workspace, reportlab, sample_resume


class ResumeHistoryManagerTests(unittest.TestCase):
    def test_repeated_records_keep_stable_pdf_links_after_cleanup_and_backfill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            candidate = workspace / "candidate.pdf"
            candidate.write_bytes(b"first")
            with history.register_generation(
                workspace, candidate, '<script>&"', "Engineer", ""
            ) as first:
                pass
            candidate.write_bytes(b"second")
            with history.register_generation(
                workspace, candidate, "Same", "Engineer", ""
            ) as second:
                pass
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_bytes(), b"first")
            root = history.history_path(workspace)
            records = history.read_records(root)
            self.assertEqual(len(records), 2)
            before = json.loads((first.parent / "record.json").read_text(encoding="utf-8"))
            self.assertEqual(before["job_url"], "")
            history.update_job_url(
                workspace, first.parent.name, 'https://example.com/jobs?a=1&b="x"'
            )
            after = json.loads((first.parent / "record.json").read_text(encoding="utf-8"))
            self.assertEqual(
                {k: v for k, v in before.items() if k != "job_url"},
                {k: v for k, v in after.items() if k != "job_url"},
            )
            reset_cache_on_start(workspace)
            self.assertEqual(first.read_bytes(), b"first")
            html = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;&amp;&quot;", html)
            self.assertNotIn("<script>", html)
            self.assertIn("&amp;b=&quot;x&quot;", html)
            self.assertIn(first.relative_to(root).as_posix(), html)
            history.update_job_url(workspace, first.parent.name, "")
            self.assertEqual(history.read_records(root)[1]["job_url"], "")

    def test_unsafe_urls_and_workspace_paths_rejected(self) -> None:
        for value in [
            "javascript:alert(1)",
            "file:///tmp/a",
            "//example.com",
            "https://",
            "https://user:password@example.com",
            "https://example.com/\nx",
            "https://example.com\\evil",
            "data:text/html,hello",
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                history.validate_job_url(value)
        with self.assertRaises(ValueError):
            history.history_path(history.PROJECT_ROOT)
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "resume_history").symlink_to(
                history.PROJECT_ROOT, target_is_directory=True
            )
            with self.assertRaises(ValueError):
                history.history_path(workspace)

    def test_failed_publication_rolls_back_record_and_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            pdf = workspace / "input.pdf"
            pdf.write_bytes(b"accepted")
            with history.register_generation(workspace, pdf, "", "", ""):
                pass
            index = history.history_path(workspace) / "index.html"
            previous = index.read_bytes()
            with self.assertRaisesRegex(OSError, "publication"):
                with history.register_generation(workspace, pdf, "", "", ""):
                    raise OSError("publication failed")
            self.assertEqual(index.read_bytes(), previous)
            self.assertEqual(len(history.read_records(index.parent)), 1)
            self.assertFalse((index.parent / ".lock").exists())

    def test_copy_or_index_failure_leaves_no_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            pdf = workspace / "input.pdf"
            pdf.write_bytes(b"accepted")
            for target in ["shutil.copyfile", "atomic_text"]:
                with self.subTest(target=target):
                    with mock.patch(
                        f"scripts.resume_history_manager.{target}", side_effect=OSError("disk")
                    ):
                        with self.assertRaises(OSError):
                            with history.register_generation(workspace, pdf, "", "", ""):
                                self.fail("must not publish")
                    self.assertEqual(history.read_records(history.history_path(workspace)), [])

    def test_set_url_index_failure_restores_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            pdf = workspace / "input.pdf"
            pdf.write_bytes(b"accepted")
            with history.register_generation(workspace, pdf, "", "", "") as historical:
                pass
            original = history.atomic_text

            def fail_index(path: Path, text: str) -> None:
                if path.name == "index.html":
                    raise OSError("index failed")
                original(path, text)

            with mock.patch.object(history, "atomic_text", side_effect=fail_index):
                with self.assertRaises(OSError):
                    history.update_job_url(
                        workspace, historical.parent.name, "https://example.com/job"
                    )
            self.assertEqual(history.read_records(historical.parent.parent)[0]["job_url"], "")

    def test_corrupt_record_and_busy_lock_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = history.history_path(Path(temp))
            with history.history_lock(root):
                with self.assertRaisesRegex(ValueError, "busy"):
                    with history.history_lock(root):
                        self.fail("must not acquire twice")
            malformed = root / ("generation-" + "a" * 32)
            malformed.mkdir()
            (malformed / "record.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid Resume"):
                history.read_records(root)

    def test_management_cli_rebuild_and_unknown_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            for extra, expected in [
                (["rebuild"], 0),
                (["set-url", "--record-id", "../escape", "--job-url", "https://example.com"], 1),
            ]:
                with mock.patch.object(sys, "argv", ["history", *extra, "--workspace", temp]):
                    with (
                        contextlib.redirect_stdout(io.StringIO()),
                        contextlib.redirect_stderr(io.StringIO()),
                    ):
                        self.assertEqual(history.main(), expected)
            self.assertIn(
                "暂无", (Path(temp) / "resume_history/index.html").read_text(encoding="utf-8")
            )


@unittest.skipIf(reportlab is None or pdfplumber is None, "PDF dependencies unavailable")
class ResumeHistoryGeneratorTests(unittest.TestCase):
    def test_format_matrix_keeps_durable_qa_pdf(self) -> None:
        from scripts import generate_final_resume as generator

        def render(name: str, content: dict, base_dir: str, layout: object) -> str:
            pdf = Path(base_dir) / name
            pdf.write_bytes(b"%PDF-synthetic-qa-reference")
            pdf.with_suffix(".docx").write_bytes(b"synthetic-docx")
            return str(pdf)

        for output_format in ("docx", "pdf", "both"):
            with self.subTest(output_format=output_format), tempfile.TemporaryDirectory() as temp:
                workspace = Path(temp)
                source = prepare_audited_workspace(workspace, sample_resume())
                argv = [
                    "generate",
                    "--workspace",
                    temp,
                    "--input-json",
                    str(source),
                    "--format",
                    output_format,
                ]
                with (
                    mock.patch.object(sys, "argv", argv),
                    mock.patch.object(generator, "generate_resume", side_effect=render),
                    mock.patch.object(
                        generator, "check_pdf_file", return_value={"verdict": "PASS"}
                    ),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(generator.main(), 0)
                output = workspace / "resume_output"
                self.assertEqual((output / "resume.docx").exists(), output_format != "pdf")
                self.assertEqual((output / "resume.pdf").exists(), output_format != "docx")
                root = history.history_path(workspace)
                record = history.read_records(root)[0]
                historical = root / record["record_id"] / "resume.pdf"
                self.assertEqual(historical.read_bytes(), b"%PDF-synthetic-qa-reference")

    def test_pair_failure_rolls_back_history_and_both_formats_without_renderer(self) -> None:
        from scripts import generate_final_resume as generator

        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            source = prepare_audited_workspace(workspace, sample_resume())
            output = workspace / "output"
            output.mkdir()
            for extension in ("pdf", "docx"):
                (output / f"resume.{extension}").write_bytes(f"previous-{extension}".encode())
            with history.register_generation(
                workspace, output / "resume.pdf", "Old", "Role", ""
            ) as prior:
                pass
            index = history.history_path(workspace) / "index.html"
            previous_index = index.read_bytes()
            original = Path.replace

            def render(name: str, content: dict, base_dir: str, layout: object) -> str:
                pdf = Path(base_dir) / name
                pdf.write_bytes(b"new-pdf")
                pdf.with_suffix(".docx").write_bytes(b"new-docx")
                return str(pdf)

            def fail_second(path: Path, target: Path) -> Path:
                if (
                    path.parent.name.startswith(".resume-staging-")
                    and target == (output / "resume.pdf").resolve()
                ):
                    self.assertEqual((output / "resume.docx").read_bytes(), b"new-docx")
                    raise OSError("second publication failed")
                return original(path, target)

            with (
                mock.patch.object(generator, "generate_resume", side_effect=render),
                mock.patch.object(generator, "check_pdf_file", return_value={"verdict": "PASS"}),
                mock.patch.object(Path, "replace", autospec=True, side_effect=fail_second),
            ):
                self.assertEqual(
                    self.run_generator(workspace, source, output, "--format", "both"), 1
                )
            for extension in ("pdf", "docx"):
                self.assertEqual(
                    (output / f"resume.{extension}").read_bytes(), f"previous-{extension}".encode()
                )
            self.assertEqual(prior.read_bytes(), b"previous-pdf")
            self.assertEqual(index.read_bytes(), previous_index)
            self.assertEqual(len(history.read_records(index.parent)), 1)

    def run_generator(self, workspace: Path, source: Path, output: Path, *extra: str) -> int:
        from scripts import generate_final_resume as generator

        argv = [
            "generate",
            "--workspace",
            str(workspace),
            "--input-json",
            str(source),
            "--output-dir",
            str(output),
            "--output-file",
            "resume.pdf",
            *extra,
        ]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            with contextlib.redirect_stderr(io.StringIO()):
                return generator.main()

    def test_history_failure_preserves_pair_before_publication_without_renderer(self) -> None:
        from scripts import generate_final_resume as generator

        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            source = prepare_audited_workspace(workspace, sample_resume())
            output = workspace / "output"
            output.mkdir()
            for extension in ("pdf", "docx"):
                (output / f"resume.{extension}").write_bytes(f"previous-{extension}".encode())

            def render(name: str, content: dict, base_dir: str, layout: object) -> str:
                pdf = Path(base_dir) / name
                pdf.write_bytes(b"new-pdf")
                pdf.with_suffix(".docx").write_bytes(b"new-docx")
                return str(pdf)

            with (
                mock.patch.object(generator, "generate_resume", side_effect=render),
                mock.patch.object(generator, "check_pdf_file", return_value={"verdict": "PASS"}),
                mock.patch.object(
                    history.shutil, "copyfile", side_effect=OSError("history disk failure")
                ),
                mock.patch.object(generator, "_publish_candidates") as publish,
            ):
                self.assertEqual(
                    self.run_generator(workspace, source, output, "--format", "both"), 1
                )
                publish.assert_not_called()
            for extension in ("pdf", "docx"):
                self.assertEqual(
                    (output / f"resume.{extension}").read_bytes(), f"previous-{extension}".encode()
                )
            self.assertEqual(history.read_records(history.history_path(workspace)), [])

    def test_repeated_generator_acceptance_and_rejection_preserve_history(self) -> None:
        from scripts import generate_final_resume as generator

        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            source = prepare_audited_workspace(workspace, sample_resume())
            output = workspace / "output"
            with mock.patch.object(generator, "check_pdf_file", return_value={"verdict": "PASS"}):
                self.assertEqual(
                    self.run_generator(
                        workspace, source, output, "--company", "Target", "--job-title", "Engineer"
                    ),
                    0,
                )
                root = history.history_path(workspace)
                record = history.read_records(root)[0]
                historical = root / record["record_id"] / "resume.pdf"
                first_bytes = historical.read_bytes()
                self.assertEqual(self.run_generator(workspace, source, output), 0)
            self.assertEqual(len(history.read_records(root)), 2)
            self.assertEqual(historical.read_bytes(), first_bytes)
            self.assertTrue(list((output / "backup").rglob("*.pdf")))
            current = (output / "resume.pdf").read_bytes()
            with mock.patch.object(generator, "check_pdf_file", return_value={"verdict": "FAIL"}):
                self.assertEqual(self.run_generator(workspace, source, output), 2)
            self.assertEqual(len(history.read_records(root)), 2)
            self.assertEqual((output / "resume.pdf").read_bytes(), current)
            self.assertEqual(historical.read_bytes(), first_bytes)
            (workspace / "cache/resume-changes.json").unlink()
            self.assertEqual(self.run_generator(workspace, source, output), 1)
            self.assertEqual(len(history.read_records(root)), 2)

    def test_history_and_partial_archive_failure_preserve_current_pdf(self) -> None:
        from scripts import generate_final_resume as generator

        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            source = prepare_audited_workspace(workspace, sample_resume())
            output = workspace / "output"
            output.mkdir()
            current = output / "resume.pdf"
            current.write_bytes(b"previous")

            original_replace = Path.replace

            def archive_then_fail(source: Path, target: Path) -> Path:
                if (
                    source.parent.name.startswith(".resume-staging-")
                    and target == current.resolve()
                ):
                    raise OSError("publication failed after archive")
                return original_replace(source, target)

            with mock.patch.object(generator, "check_pdf_file", return_value={"verdict": "PASS"}):
                with mock.patch.object(history, "atomic_text", side_effect=OSError("disk")):
                    self.assertEqual(self.run_generator(workspace, source, output), 1)
                self.assertEqual(current.read_bytes(), b"previous")
                with mock.patch.object(
                    Path, "replace", autospec=True, side_effect=archive_then_fail
                ):
                    self.assertEqual(self.run_generator(workspace, source, output), 1)
                self.assertEqual(current.read_bytes(), b"previous")
                self.assertEqual(history.read_records(history.history_path(workspace)), [])

    def test_generator_rejects_default_output_symlink_and_history_overlap(self) -> None:
        from scripts import generate_final_resume as generator

        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            source = prepare_audited_workspace(workspace, sample_resume())
            (workspace / "resume_output").symlink_to(history.PROJECT_ROOT, target_is_directory=True)
            argv = [
                "generate",
                "--workspace",
                temp,
                "--input-json",
                str(source),
                "--output-file",
                "resume.pdf",
            ]
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(generator.main(), 1)
            self.assertEqual(self.run_generator(workspace, source, workspace / "resume_history"), 1)
            self.assertFalse((workspace / "resume_history").exists())

    def test_standard_default_and_external_legacy_output(self) -> None:
        from scripts import generate_final_resume as generator

        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "candidate"
            source = prepare_audited_workspace(workspace, sample_resume())
            output = Path(temp) / "legacy-output"
            with mock.patch.object(generator, "check_pdf_file", return_value={"verdict": "PASS"}):
                self.assertEqual(self.run_generator(workspace, source, output), 0)
            self.assertEqual(len(history.read_records(history.history_path(workspace))), 1)
            # Redirect Python's workspace default without hiding user-installed
            # fonts from the real Fontconfig/LibreOffice subprocesses via HOME.
            with mock.patch("scripts.resume_shared.Path.home", return_value=Path(temp)):
                with mock.patch.object(
                    sys,
                    "argv",
                    ["generate", "--input-json", str(source), "--output-file", "resume.pdf"],
                ):
                    args = generator.parse_args()
                    self.assertEqual(args.workspace, Path(temp) / "Documents/MonkeyResume")
                    self.assertIsNone(args.output_dir)
                    with mock.patch.object(
                        generator, "check_pdf_file", return_value={"verdict": "PASS"}
                    ):
                        with contextlib.redirect_stdout(io.StringIO()):
                            self.assertEqual(generator.main(), 0)
                self.assertTrue(
                    (Path(temp) / "Documents/MonkeyResume/resume_output/resume.pdf").is_file()
                )


if __name__ == "__main__":
    unittest.main()
