"""Windows Job Object containment for suspended, trusted worker processes.

This module provides process-tree lifecycle management only. It is not a
security sandbox and does not enforce CPU, memory, filesystem, or network policy.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import subprocess
import threading
import time


if os.name == "nt":
    _DWORD = wintypes.DWORD
    _HANDLE = wintypes.HANDLE
    _SIZE_T = ctypes.c_size_t
    _ULONG_PTR = ctypes.c_size_t
    _LARGE_INTEGER = ctypes.c_longlong

    class _BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", _LARGE_INTEGER),
            ("PerJobUserTimeLimit", _LARGE_INTEGER),
            ("LimitFlags", _DWORD),
            ("MinimumWorkingSetSize", _SIZE_T),
            ("MaximumWorkingSetSize", _SIZE_T),
            ("ActiveProcessLimit", _DWORD),
            ("Affinity", _ULONG_PTR),
            ("PriorityClass", _DWORD),
            ("SchedulingClass", _DWORD),
        ]

    class _IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BasicLimitInformation),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", _SIZE_T),
            ("JobMemoryLimit", _SIZE_T),
            ("PeakProcessMemoryUsed", _SIZE_T),
            ("PeakJobMemoryUsed", _SIZE_T),
        ]

    class _BasicAccountingInformation(ctypes.Structure):
        _fields_ = [
            ("TotalUserTime", _LARGE_INTEGER),
            ("TotalKernelTime", _LARGE_INTEGER),
            ("ThisPeriodTotalUserTime", _LARGE_INTEGER),
            ("ThisPeriodTotalKernelTime", _LARGE_INTEGER),
            ("TotalPageFaultCount", _DWORD),
            ("TotalProcesses", _DWORD),
            ("ActiveProcesses", _DWORD),
            ("TotalTerminatedProcesses", _DWORD),
        ]

    class _ThreadEntry32(ctypes.Structure):
        _fields_ = [
            ("dwSize", _DWORD),
            ("cntUsage", _DWORD),
            ("th32ThreadID", _DWORD),
            ("th32OwnerProcessID", _DWORD),
            ("tpBasePri", ctypes.c_long),
            ("tpDeltaPri", ctypes.c_long),
            ("dwFlags", _DWORD),
        ]


def _windows_api():
    if os.name != "nt":
        raise OSError("Windows Job Objects are available only on Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry32)]
    kernel32.Thread32First.restype = wintypes.BOOL
    kernel32.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry32)]
    kernel32.Thread32Next.restype = wintypes.BOOL
    kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenThread.restype = wintypes.HANDLE
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD
    return kernel32


def _raise_last_error(message: str) -> None:
    error = ctypes.get_last_error()
    raise OSError(error, f"{message}: {ctypes.FormatError(error).strip()}")


def _resume_only_suspended_primary_thread(kernel32, process_id: int) -> None:
    """Resume the sole thread of a process created with CREATE_SUSPENDED.

    Since the primary thread has not run, it cannot have created any other
    threads. Requiring exactly one enumerated thread fails closed if this
    invariant cannot be established.
    """
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
    invalid = ctypes.c_void_p(-1).value
    if not snapshot or snapshot == invalid:
        _raise_last_error("CreateToolhelp32Snapshot failed")
    thread_handle = None
    try:
        entry = _ThreadEntry32()
        entry.dwSize = ctypes.sizeof(entry)
        matches: list[int] = []
        ok = kernel32.Thread32First(snapshot, ctypes.byref(entry))
        while ok:
            if entry.th32OwnerProcessID == process_id:
                matches.append(int(entry.th32ThreadID))
            ok = kernel32.Thread32Next(snapshot, ctypes.byref(entry))
        if len(matches) != 1:
            raise OSError(f"expected one suspended primary thread, found {len(matches)}")
        thread_handle = kernel32.OpenThread(0x0002, False, matches[0])
        if not thread_handle:
            _raise_last_error("OpenThread failed")
        previous_count = kernel32.ResumeThread(thread_handle)
        if previous_count == 0xFFFFFFFF:
            _raise_last_error("ResumeThread failed")
        if previous_count != 1:
            raise OSError(
                f"primary thread had unexpected suspend count {previous_count}; "
                "worker was not resumed under the expected invariant"
            )
    finally:
        if thread_handle:
            kernel32.CloseHandle(thread_handle)
        kernel32.CloseHandle(snapshot)


class WindowsJob:
    """Owns one kill-on-close Job Object and its assigned worker process tree."""

    def __init__(self) -> None:
        self._kernel32 = _windows_api()
        self._handle = self._kernel32.CreateJobObjectW(None, None)
        if not self._handle:
            _raise_last_error("CreateJobObjectW failed")
        self._closed = False
        self._lock = threading.RLock()
        limits = _ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # KILL_ON_JOB_CLOSE
        if not self._kernel32.SetInformationJobObject(
            self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error, f"SetInformationJobObject failed: {ctypes.FormatError(error).strip()}")

    def assign_suspended(self, process: subprocess.Popen[bytes]) -> None:
        with self._lock:
            if self._closed or not self._handle:
                raise RuntimeError("Job Object is closed")
            if process.poll() is not None:
                raise RuntimeError("cannot assign an exited worker")
            process_handle = wintypes.HANDLE(int(process._handle))
            if not self._kernel32.AssignProcessToJobObject(self._handle, process_handle):
                _raise_last_error("AssignProcessToJobObject failed; worker remains suspended")
            try:
                _resume_only_suspended_primary_thread(self._kernel32, process.pid)
            except Exception:
                self.terminate()
                raise

    def terminate(self, exit_code: int = 1) -> None:
        with self._lock:
            if self._closed or not self._handle:
                return
            if not self._kernel32.TerminateJobObject(self._handle, exit_code):
                error = ctypes.get_last_error()
                # An already-empty job may reject termination; verify emptiness.
                if self.active_processes != 0:
                    raise OSError(error, f"TerminateJobObject failed: {ctypes.FormatError(error).strip()}")

    @property
    def active_processes(self) -> int:
        with self._lock:
            if self._closed or not self._handle:
                return 0
            info = _BasicAccountingInformation()
            returned = wintypes.DWORD()
            if not self._kernel32.QueryInformationJobObject(
                self._handle, 1, ctypes.byref(info), ctypes.sizeof(info), ctypes.byref(returned)
            ):
                _raise_last_error("QueryInformationJobObject failed")
            return int(info.ActiveProcesses)

    def wait_empty(self, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while True:
            if self.active_processes == 0:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            handle = self._handle
            if handle and not self._kernel32.CloseHandle(handle):
                _raise_last_error("CloseHandle(Job Object) failed")
            self._handle = None
            self._closed = True

    def __enter__(self) -> "WindowsJob":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.active_processes:
            self.terminate()
            self.wait_empty(2.0)
        self.close()
