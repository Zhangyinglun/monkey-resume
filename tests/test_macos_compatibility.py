"""macOS compatibility guards, plus real POSIX checks on native CI runners."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.candidate_cache import validate_workspace
from templates.office_tools import find_soffice, run_office


class MacCompatibilityTests(unittest.TestCase):
    def test_posix_workspace_canonicalizes_system_prefix_aliases(self) -> None:
        # macOS tempfile paths commonly enter through /var -> /private/var.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            canonical = root / "private-var"
            canonical.mkdir()
            alias = root / "var"
            try:
                alias.symlink_to(canonical, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Symlink creation unavailable: {error}")
            with patch("scripts.candidate_cache.os", SimpleNamespace(name="posix")):
                self.assertEqual(validate_workspace(alias / "candidate"), canonical / "candidate")

    def test_office_import_does_not_load_windows_specific_code(self) -> None:
        code = """
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'templates.windows_process':
        raise RuntimeError('Windows-specific module imported on POSIX')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import templates.office_tools
"""
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=10, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_macos_app_bundle_is_found_without_path_entry(self) -> None:
        with (
            patch("templates.office_tools.platform.system", return_value="Darwin"),
            patch("templates.office_tools.shutil.which", return_value=None),
            patch("templates.office_tools.Path.is_file", return_value=True),
        ):
            executable = find_soffice()
        self.assertIsNotNone(executable)
        expected = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice").resolve()
        self.assertEqual(Path(executable), expected)

    @unittest.skipUnless(os.name == "posix", "Requires native POSIX process groups")
    def test_native_posix_timeout_reaps_the_converter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "converter.pid"
            code = (
                "import os,sys,time; from pathlib import Path; "
                "Path(sys.argv[1]).write_text(str(os.getpid()),encoding='utf-8'); "
                "time.sleep(60)"
            )
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    run_office([sys.executable, "-c", code, str(marker)], timeout=1)
                self.assertTrue(marker.is_file(), "Converter did not reach its startup marker")
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(marker.read_text(encoding="utf-8")), 0)
            finally:
                if marker.is_file():
                    try:
                        os.kill(int(marker.read_text(encoding="utf-8")), 9)
                    except ProcessLookupError:
                        pass

    @unittest.skipUnless(os.name == "posix", "Requires native POSIX process groups")
    def test_native_posix_timeout_stops_descendant_after_launcher_exits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            pid_file, heartbeat = root / "descendant.pid", root / "heartbeat.txt"
            child = (
                "import sys,time; from pathlib import Path\n"
                "path=Path(sys.argv[1])\n"
                "while True:\n"
                "    with path.open('a',encoding='utf-8') as stream: stream.write('tick\\n')\n"
                "    time.sleep(0.05)\n"
            )
            parent = (
                "import subprocess,sys; from pathlib import Path; "
                "p=subprocess.Popen([sys.executable,'-c',sys.argv[2],sys.argv[3]]); "
                "Path(sys.argv[1]).write_text(str(p.pid),encoding='utf-8')"
            )
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    run_office(
                        [sys.executable, "-c", parent, str(pid_file), child, str(heartbeat)],
                        timeout=1,
                    )
                self.assertTrue(pid_file.is_file(), "Launcher did not start its descendant")
                self.assertTrue(heartbeat.is_file(), "Descendant did not reach its startup marker")
                stopped = heartbeat.read_bytes()
                time.sleep(0.2)
                self.assertEqual(heartbeat.read_bytes(), stopped, "Descendant kept running after timeout")
            finally:
                if pid_file.is_file():
                    try:
                        os.kill(int(pid_file.read_text(encoding="utf-8")), 9)
                    except ProcessLookupError:
                        pass
