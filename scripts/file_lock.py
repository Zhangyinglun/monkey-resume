"""OS-backed exclusive file locks that never follow the final path's links."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def exclusive_file_lock(path: Path) -> Iterator[None]:
    """Wait for a lock, releasing its kernel handle even when the body raises."""
    if os.name == "nt":
        with _windows_lock(path):
            yield
    else:
        import fcntl

        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


@contextmanager
def _windows_lock(path: Path) -> Iterator[None]:
    """Open the reparse point itself, reject it, then lock a byte synchronously.

    Denying delete sharing also prevents replacement of the lock file while any
    writer holds or waits on it. LockFileEx waits in the kernel, unlike msvcrt's
    limited ten-attempt blocking lock.
    """
    import ctypes
    from ctypes import wintypes

    class AttributeTagInfo(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("tag", wintypes.DWORD)]

    class Overlapped(ctypes.Structure):
        _fields_ = [
            ("internal", ctypes.c_size_t), ("internal_high", ctypes.c_size_t),
            ("offset", wintypes.DWORD), ("offset_high", wintypes.DWORD),
            ("event", wintypes.HANDLE),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
    kernel.LockFileEx.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.DWORD, ctypes.POINTER(Overlapped),
    ]
    kernel.LockFileEx.restype = wintypes.BOOL
    kernel.UnlockFileEx.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(Overlapped),
    ]
    kernel.UnlockFileEx.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL

    # GENERIC_READ | GENERIC_WRITE, SHARE_READ | SHARE_WRITE, OPEN_ALWAYS,
    # FILE_FLAG_OPEN_REPARSE_POINT. Never silently follow a lock-file symlink.
    handle = kernel.CreateFileW(str(path), 0xC0000000, 0x3, None, 4, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = AttributeTagInfo()
        if not kernel.GetFileInformationByHandleEx(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        if info.attributes & (0x400 | 0x10):  # REPARSE_POINT | DIRECTORY
            raise ValueError(f"Unsafe reparse point or directory lock: {path}")
        overlapped = Overlapped()
        if not kernel.LockFileEx(handle, 2, 0, 1, 0, ctypes.byref(overlapped)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield
        finally:
            if not kernel.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(overlapped)):
                raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)
