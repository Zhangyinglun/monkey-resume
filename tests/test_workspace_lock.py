"""Workspace transactions serialize across processes, including native Windows."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from scripts.candidate_cache import workspace_lock

ROOT = Path(__file__).resolve().parents[1]
CHILD = """
import sys
from pathlib import Path
from scripts.candidate_cache import workspace_lock
workspace = Path(sys.argv[1])
print('ready', flush=True)
with workspace_lock(workspace):
    print('acquired', flush=True)
"""


class WorkspaceLockTests(unittest.TestCase):
    def test_another_process_waits_until_the_workspace_is_released(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory).resolve()
            with workspace_lock(workspace):
                child = subprocess.Popen(
                    [sys.executable, "-c", CHILD, str(workspace)], cwd=ROOT,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                )
                try:
                    ready: list[str] = []
                    reader = threading.Thread(target=lambda: ready.append(child.stdout.readline()))
                    reader.start()
                    reader.join(timeout=5)
                    if reader.is_alive():
                        child.kill()
                        reader.join(timeout=5)
                        self.fail("Child did not reach the lock attempt within five seconds")
                    self.assertEqual(ready, ["ready\n"])
                    with self.assertRaises(subprocess.TimeoutExpired):
                        child.communicate(timeout=0.5)
                except BaseException:
                    child.kill()
                    child.communicate(timeout=5)
                    raise
            try:
                stdout, stderr = child.communicate(timeout=10)
                self.assertEqual(child.returncode, 0, stderr)
                self.assertEqual(stdout.splitlines(), ["acquired"])
            finally:
                if child.poll() is None:
                    child.kill()
                    child.communicate(timeout=5)

    def test_exception_releases_the_workspace_for_a_new_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory).resolve()
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                with workspace_lock(workspace):
                    raise RuntimeError("interrupted")
            result = subprocess.run(
                [sys.executable, "-c", CHILD, str(workspace)], cwd=ROOT,
                capture_output=True, text=True, timeout=10, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("acquired", result.stdout)

    def test_lock_symlink_cannot_modify_an_external_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            workspace = root / "workspace"
            (workspace / "cache").mkdir(parents=True)
            outside = root / "outside.txt"
            outside.write_text("preserve", encoding="utf-8")
            try:
                (workspace / "cache/import.lock").symlink_to(outside)
            except OSError as error:
                self.skipTest(f"Symlink creation unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                with workspace_lock(workspace):
                    self.fail("Symlink lock was accepted")
            self.assertEqual(outside.read_text(encoding="utf-8"), "preserve")

    @unittest.skipUnless(os.name == "nt", "Windows directory junction")
    def test_cache_junction_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            workspace, outside = root / "workspace", root / "outside"
            workspace.mkdir()
            outside.mkdir()
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(workspace / "cache"), str(outside)],
                capture_output=True, timeout=10, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                with workspace_lock(workspace):
                    self.fail("Junction cache was accepted")
            self.assertFalse((outside / "import.lock").exists())
