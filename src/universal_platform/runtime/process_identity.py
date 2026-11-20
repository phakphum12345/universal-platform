"""Immutable OS process identity snapshots for supervised worker recovery.

Identity capture is intentionally platform-specific. Unsupported platforms fail
closed instead of returning a PID-only identity that could be confused after
PID reuse. This module does not inspect liveness or terminate processes.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Any


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    """Stable process identity captured before a start-gated worker is released."""

    platform: str
    pid: int
    creation_token: str
    host_boot_id: str | None
    worker_id: str
    host_instance_id: str
    process_group_id: int | None = None
    session_id: int | None = None
    job_object_id: str | None = None

    def __post_init__(self) -> None:
        if self.platform not in {"linux", "windows"}:
            raise ValueError("unsupported process identity platform")
        if isinstance(self.pid, bool) or not isinstance(self.pid, int) or self.pid <= 0:
            raise ValueError("pid must be a positive integer")
        for name, value in (
            ("creation_token", self.creation_token),
            ("worker_id", self.worker_id),
            ("host_instance_id", self.host_instance_id),
        ):
            if not isinstance(value, str) or not value.strip() or "\x00" in value:
                raise ValueError(f"{name} must be a non-empty NUL-free string")
        if self.host_boot_id is not None and (
            not isinstance(self.host_boot_id, str) or not self.host_boot_id.strip()
        ):
            raise ValueError("host_boot_id must be a non-empty string or None")
        for name, value in (
            ("process_group_id", self.process_group_id),
            ("session_id", self.session_id),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
            ):
                raise ValueError(f"{name} must be a positive integer or None")
        if self.platform == "linux" and (
            self.host_boot_id is None
            or self.process_group_id is None
            or self.session_id is None
        ):
            raise ValueError("Linux identity requires boot, process-group and session tokens")

    def to_dict(self) -> dict[str, object]:
        return {
            "platform": self.platform,
            "pid": self.pid,
            "creation_token": self.creation_token,
            "host_boot_id": self.host_boot_id,
            "worker_id": self.worker_id,
            "host_instance_id": self.host_instance_id,
            "process_group_id": self.process_group_id,
            "session_id": self.session_id,
            "job_object_id": self.job_object_id,
        }


def _linux_process_identity(
    pid: int,
    *,
    proc_root: Path,
    worker_id: str,
    host_instance_id: str,
) -> ProcessIdentity:
    stat_path = proc_root / str(pid) / "stat"
    stat_text = stat_path.read_text(encoding="ascii")
    closing = stat_text.rfind(")")
    if closing < 0:
        raise OSError("Linux process stat record is malformed")
    fields = stat_text[closing + 1 :].split()
    # The first token after comm is field 3 (state); starttime is field 22.
    if len(fields) < 20:
        raise OSError("Linux process stat record is incomplete")
    state = fields[0]
    if state in {"Z", "X"}:
        raise ProcessLookupError(f"process {pid} is not live")
    try:
        process_group_id = int(fields[2])
        session_id = int(fields[3])
        start_ticks = int(fields[19])
    except (ValueError, IndexError) as error:
        raise OSError("Linux process identity fields are invalid") from error
    if min(process_group_id, session_id, start_ticks) <= 0:
        raise OSError("Linux process identity fields must be positive")
    boot_id = (proc_root / "sys/kernel/random/boot_id").read_text(
        encoding="ascii"
    ).strip()
    if not boot_id:
        raise OSError("Linux host boot identity is unavailable")
    return ProcessIdentity(
        platform="linux",
        pid=pid,
        creation_token=str(start_ticks),
        host_boot_id=boot_id,
        worker_id=worker_id,
        host_instance_id=host_instance_id,
        process_group_id=process_group_id,
        session_id=session_id,
    )


def _windows_process_identity(
    pid: int,
    *,
    worker_id: str,
    host_instance_id: str,
    job_object_id: str | None,
) -> ProcessIdentity:
    if os.name != "nt":
        raise OSError("Windows process identity is unavailable on this platform")
    import ctypes
    from ctypes import wintypes

    class FileTime(ctypes.Structure):
        _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        error = ctypes.get_last_error()
        raise OSError(error, "OpenProcess failed while capturing worker identity")
    try:
        created = FileTime()
        exited = FileTime()
        kernel = FileTime()
        user = FileTime()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            error = ctypes.get_last_error()
            raise OSError(error, "GetProcessTimes failed while capturing worker identity")
        creation_ticks = (int(created.high) << 32) | int(created.low)
        if creation_ticks <= 0:
            raise OSError("Windows process creation token is invalid")
    finally:
        kernel32.CloseHandle(handle)
    return ProcessIdentity(
        platform="windows",
        pid=pid,
        creation_token=f"{creation_ticks:016x}",
        host_boot_id=None,
        worker_id=worker_id,
        host_instance_id=host_instance_id,
        job_object_id=job_object_id,
    )


def capture_process_identity(
    process: Any,
    *,
    worker_id: str,
    host_instance_id: str,
    job_object_id: str | None = None,
    proc_root: str | os.PathLike[str] = "/proc",
) -> ProcessIdentity:
    """Capture PID plus an OS creation token; never fall back to PID alone."""
    pid = getattr(process, "pid", None)
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("process must expose a positive integer pid")
    if not isinstance(worker_id, str) or not worker_id.strip():
        raise ValueError("worker_id must be non-empty")
    if not isinstance(host_instance_id, str) or not host_instance_id.strip():
        raise ValueError("host_instance_id must be non-empty")
    if job_object_id is not None and (
        not isinstance(job_object_id, str) or not job_object_id.strip()
    ):
        raise ValueError("job_object_id must be a non-empty string or None")
    if os.name == "nt":
        return _windows_process_identity(
            pid,
            worker_id=worker_id,
            host_instance_id=host_instance_id,
            job_object_id=job_object_id,
        )
    if sys_platform_linux():
        return _linux_process_identity(
            pid,
            proc_root=Path(proc_root),
            worker_id=worker_id,
            host_instance_id=host_instance_id,
        )
    raise NotImplementedError("safe process creation identity is not implemented on this OS")


def sys_platform_linux() -> bool:
    return sys.platform == "linux"


__all__ = ["ProcessIdentity", "capture_process_identity"]
