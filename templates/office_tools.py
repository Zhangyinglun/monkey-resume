"""Discover the local office CLI without modifying PATH or launching a GUI."""
from __future__ import annotations

import os
import platform
import shutil
import signal
import subprocess
from pathlib import Path


def find_soffice() -> str | None:
    """Prefer PATH installations and Windows' waitable console launcher."""
    windows = platform.system() == "Windows"
    names = ("soffice.com", "soffice.exe", "soffice", "libreoffice") if windows else ("soffice", "libreoffice")
    for name in names:
        found = shutil.which(name)
        if found:
            path = Path(found).resolve()
            console = path.with_name("soffice.com")
            return str(console if windows and console.is_file() else path)
    if windows:
        roots = dict.fromkeys(
            os.environ.get(key, default)
            for key, default in (
                ("ProgramFiles", "C:/Program Files"),
                ("ProgramW6432", "C:/Program Files"),
                ("ProgramFiles(x86)", "C:/Program Files (x86)"),
            )
        )
        for root in roots:
            if not root:
                continue
            for name in ("soffice.com", "soffice.exe"):
                candidate = Path(root) / "LibreOffice/program" / name
                if candidate.is_file():
                    return str(candidate.resolve())
    elif platform.system() == "Darwin":
        candidate = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def run_office(command: list[str], *, env: dict[str, str] | None = None,
               timeout: float = 30) -> subprocess.CompletedProcess[str]:
    """Bound conversion and own its descendants even after the launcher exits."""
    if platform.system() == "Windows":
        from templates.windows_process import run_windows_process

        return run_windows_process(command, env=env, timeout=timeout)
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True,
                               start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        finally:
            try:
                process.kill()
            finally:
                process.communicate(timeout=5)
