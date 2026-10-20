from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.render_pdf_reference import render_reference
from templates import office_tools, windows_process
from templates.docx_resume_template import export_pdf
from vendor.openai_doc import render_docx


class OfficeDiscoveryTests(unittest.TestCase):
    def test_windows_path_installation_uses_console_sibling_before_standard_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            custom = root / "custom office"
            custom.mkdir()
            for name in ("soffice.exe", "soffice.com"):
                (custom / name).touch()
            with (
                mock.patch.object(office_tools.platform, "system", return_value="Windows"),
                mock.patch.object(office_tools.shutil, "which", side_effect=lambda name: str(custom / name) if name == "soffice.exe" else None),
            ):
                self.assertEqual(office_tools.find_soffice(), str(custom / "soffice.com"))

    def test_windows_standard_install_is_found_without_changing_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            program_files = Path(directory).resolve()
            program = program_files / "LibreOffice/program"
            program.mkdir(parents=True)
            (program / "soffice.com").touch()
            with (
                mock.patch.object(office_tools.platform, "system", return_value="Windows"),
                mock.patch.object(office_tools.shutil, "which", return_value=None),
                mock.patch.dict(office_tools.os.environ, {"ProgramFiles": str(program_files), "PATH": "unchanged"}),
            ):
                self.assertEqual(office_tools.find_soffice(), str(program / "soffice.com"))
                self.assertEqual(office_tools.os.environ["PATH"], "unchanged")


class OfficeProcessTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows process lifetime")
    def test_timeout_stops_descendant_even_after_its_launcher_exits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "descendant.pid"
            code = (
                "import subprocess,sys; from pathlib import Path; "
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                "Path(sys.argv[1]).write_text(str(child.pid),encoding='utf-8')"
            )
            alive = False
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    office_tools.run_office([sys.executable, "-c", code, str(pid_file)], timeout=1)
                self.assertTrue(pid_file.is_file(), "Descendant did not start")
                alive = self._windows_pid_is_running(int(pid_file.read_text(encoding="utf-8")))
            finally:
                # A red test must not leave its synthetic sixty-second sleeper.
                if pid_file.is_file():
                    subprocess.run(
                        ["taskkill", "/PID", pid_file.read_text(encoding="utf-8"), "/T", "/F"],
                        capture_output=True, timeout=10, check=False,
                    )
            self.assertFalse(alive, "Timeout left a live descendant after its launcher exited")

    @unittest.skipUnless(os.name == "nt", "Windows process lifetime")
    def test_normal_nonzero_return_also_stops_detached_pipe_descendants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "descendant.pid"
            code = (
                "import subprocess,sys; from pathlib import Path; "
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],"
                "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                "Path(sys.argv[1]).write_text(str(child.pid),encoding='utf-8'); "
                "print('finished'); raise SystemExit(7)"
            )
            try:
                result = office_tools.run_office([sys.executable, "-c", code, str(pid_file)], timeout=5)
                self.assertEqual(result.returncode, 7)
                self.assertEqual(result.stdout.strip(), "finished")
                self.assertFalse(self._windows_pid_is_running(int(pid_file.read_text(encoding="utf-8"))))
            finally:
                if pid_file.is_file():
                    subprocess.run(
                        ["taskkill", "/PID", pid_file.read_text(encoding="utf-8"), "/T", "/F"],
                        capture_output=True, timeout=10, check=False,
                    )

    @unittest.skipUnless(os.name == "nt", "Windows process lifetime")
    def test_assignment_or_resume_failure_reaps_the_suspended_parent_without_running_it(self) -> None:
        real_popen = subprocess.Popen
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "must-not-run.txt"
            code = "from pathlib import Path; import sys; Path(sys.argv[1]).touch()"
            for failure in ("assignment", "resume"):
                spawned: list[subprocess.Popen[str]] = []

                def spawn(*args: object, **kwargs: object) -> subprocess.Popen[str]:
                    process = real_popen(*args, **kwargs)
                    spawned.append(process)
                    return process

                job = windows_process.WindowsJob()
                fault = (
                    mock.patch.object(job, "assign_and_resume", side_effect=OSError("assignment failed"))
                    if failure == "assignment" else
                    mock.patch.object(job._kernel, "ResumeThread", side_effect=OSError("resume failed"))
                )
                with (
                    self.subTest(failure=failure), fault,
                    mock.patch.object(windows_process, "WindowsJob", return_value=job),
                    mock.patch.object(windows_process.subprocess, "Popen", side_effect=spawn),
                ):
                    try:
                        with self.assertRaisesRegex(OSError, "failed"):
                            office_tools.run_office([sys.executable, "-c", code, str(marker)], timeout=1)
                        self.assertEqual(len(spawned), 1)
                        self.assertIsNotNone(spawned[0].poll())
                        self.assertFalse(marker.exists(), "Suspended process ran before successful job setup")
                    finally:
                        # Keep a failing cleanup assertion from leaking a suspended parent.
                        for process in spawned:
                            process.kill()
                            process.communicate(timeout=5)
                        job.close()

    @unittest.skipUnless(os.name == "nt", "Windows process lifetime")
    def test_process_probe_still_detects_a_live_control_process(self) -> None:
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            self.assertTrue(self._windows_pid_is_running(process.pid, timeout_ms=30))
        finally:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True, timeout=10, check=False,
            )
            process.kill()
            process.communicate(timeout=5)

    @staticmethod
    def _windows_pid_is_running(pid: int, *, timeout_ms: int = 5000) -> bool:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.WaitForSingleObject.restype = ctypes.c_uint32
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 87:  # ERROR_INVALID_PARAMETER: PID no longer exists
                return False
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            # Job accounting can reach zero just before the exit handle signals.
            # Wait for the native completion signal rather than sampling once.
            result = kernel.WaitForSingleObject(handle, timeout_ms)
            if result == 0:
                return False
            if result == 258:
                return True
            raise ctypes.WinError(ctypes.get_last_error())
        finally:
            if handle:
                kernel.CloseHandle(handle)

    def test_posix_group_cleanup_on_return_timeout_and_interrupt(self) -> None:
        for error in (None, subprocess.TimeoutExpired("office", 30), KeyboardInterrupt()):
            process = mock.Mock(pid=1234, returncode=7)
            process.communicate.side_effect = [error or ("out", "err"), ("", "")]
            with (
                self.subTest(error=type(error).__name__),
                mock.patch.object(office_tools.platform, "system", return_value="Linux"),
                mock.patch.object(office_tools.subprocess, "Popen", return_value=process) as spawn,
                mock.patch.object(office_tools.os, "killpg", create=True) as kill_group,
                mock.patch.object(office_tools.signal, "SIGKILL", 9, create=True),
            ):
                if error is None:
                    self.assertEqual(office_tools.run_office(["office"]).returncode, 7)
                else:
                    with self.assertRaises(type(error)):
                        office_tools.run_office(["office"])
            self.assertTrue(spawn.call_args.kwargs["start_new_session"])
            kill_group.assert_called_once_with(1234, 9)
            process.kill.assert_called_once()
            self.assertEqual(process.communicate.call_args_list, [mock.call(timeout=30), mock.call(timeout=5)])


class PreviewConversionTests(unittest.TestCase):
    def test_preview_poppler_calls_have_finite_timeouts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            pdf = root / "resume.pdf"
            pdf.touch()
            with (
                mock.patch.object(render_docx, "convert_to_pdf", return_value=str(pdf)),
                mock.patch.object(render_docx, "pdfinfo_from_path", return_value={"Page size": "595 x 842 pts"}) as info,
                mock.patch.object(render_docx, "convert_from_path", return_value=[]) as images,
            ):
                render_docx.calc_dpi_via_pdf(str(root / "resume.docx"), 1600, 2000)
                render_docx.rasterize(str(root / "resume.docx"), str(root / "preview"), 96)
            self.assertEqual(info.call_args.kwargs["timeout"], 15)
            self.assertEqual(images.call_args.kwargs["timeout"], 30)

    def test_export_and_preview_use_the_discovered_absolute_office_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "resume.docx"
            source.touch()
            executable = str(root / "office/soffice.com")

            def convert(command: list[str], **kwargs: object) -> mock.Mock:
                source.with_suffix(".pdf").write_bytes(b"%PDF mock")
                return mock.Mock(returncode=0, stdout="", stderr="")

            with (
                mock.patch("templates.docx_resume_template.find_soffice", return_value=executable),
                mock.patch("templates.docx_resume_template.conversion_environment", return_value={}),
                mock.patch("templates.docx_resume_template.validate_pdf_fonts"),
                mock.patch("templates.docx_resume_template.run_office", side_effect=convert) as export_run,
            ):
                export_pdf(source)
            self.assertEqual(export_run.call_args.args[0][0], executable)

            with (
                mock.patch.object(render_docx, "find_soffice", return_value=executable),
                mock.patch.object(render_docx, "run_cmd_no_check") as preview_run,
            ):
                render_docx.convert_to_pdf(str(source), str(root / "profile"), directory, "resume")
            self.assertEqual(preview_run.call_args.args[0][0], executable)

    def test_preview_does_not_launch_an_outer_python_process_or_change_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "resume.docx"
            source.touch()
            with (
                mock.patch("scripts.render_pdf_reference.conversion_environment", return_value={"PATH": "unchanged"}),
                mock.patch("scripts.render_pdf_reference.ensure_system_tools"),
                mock.patch("scripts.render_pdf_reference.rasterize") as rasterize,
                mock.patch("subprocess.run") as run,
            ):
                render_reference(source, root / "preview", dpi=96)
            rasterize.assert_called_once_with(str(source), str(root / "preview"), 96, env={"PATH": "unchanged"})
            run.assert_not_called()

    def test_profile_argument_is_an_escaped_absolute_file_uri(self) -> None:
        with tempfile.TemporaryDirectory(prefix="resume 空格 ") as directory:
            root = Path(directory).resolve()
            profile = root / "profile 空格"

            def convert(command: list[str], **kwargs: object) -> None:
                if command[command.index("--convert-to") + 1] == "odt":
                    (root / "resume.odt").touch()

            with (
                mock.patch.object(render_docx, "find_soffice", return_value="mock-soffice"),
                mock.patch.object(render_docx, "run_cmd_no_check", side_effect=convert) as run,
            ):
                render_docx.convert_to_pdf(str(root / "resume.docx"), str(profile), directory, "resume")
            self.assertEqual(len(run.call_args_list), 3)
            for call in run.call_args_list:
                self.assertEqual(call.args[0][1], "-env:UserInstallation=" + profile.as_uri())


if __name__ == "__main__":
    unittest.main()
