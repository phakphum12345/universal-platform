"""Bounded, allow-listed OS process supervision for trusted Python workers.

This is process supervision, not a security sandbox. Do not run untrusted code
with this adapter; use an OS/container sandbox with an explicit policy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from typing import Mapping, Sequence

from .windows_job import WindowsJob


@dataclass(frozen=True, slots=True)
class WorkerSpec:
    worker_id: str
    executable: str
    arguments: tuple[str, ...] = ()
    working_directory: str = "."
    environment: Mapping[str, str] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    terminate_grace_seconds: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.worker_id, str) or not self.worker_id.strip():
            raise ValueError("worker_id must be non-empty")
        if not isinstance(self.executable, str) or not self.executable.strip():
            raise ValueError("executable must be non-empty")
        if any(not isinstance(item, str) or "\x00" in item for item in self.arguments):
            raise ValueError("arguments must be NUL-free strings")
        if not isinstance(self.working_directory, str) or not self.working_directory.strip():
            raise ValueError("working_directory must be non-empty")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)) or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if isinstance(self.terminate_grace_seconds, bool) or not isinstance(self.terminate_grace_seconds, (int, float)) or not math.isfinite(self.terminate_grace_seconds) or self.terminate_grace_seconds < 0:
            raise ValueError("terminate_grace_seconds must be finite and non-negative")
        for key, value in self.environment.items():
            if not isinstance(key, str) or not isinstance(value, str) or not key or "=" in key or "\x00" in key or "\x00" in value:
                raise ValueError("environment entries must have valid names and NUL-free string values")


@dataclass(frozen=True, slots=True)
class WorkerResult:
    worker_id: str
    exit_code: int | None
    timed_out: bool
    cancelled: bool
    duration_seconds: float
    stdout: str
    stderr: str
    output_truncated: bool


class PythonProcessSupervisor:
    """Runs trusted, explicitly allow-listed executables without a shell.

    Working directories are confined beneath a configured root. Retained
    output is bounded per stream. POSIX workers run in a new session, and
    cleanup targets the whole process group even if its leader has exited.
    Windows workers are created suspended, assigned to a private kill-on-close
    Job Object, and resumed only after assignment succeeds. This manages the
    worker process tree; it is not an OS security sandbox.
    """

    def __init__(
        self,
        *,
        working_root: str | os.PathLike[str],
        allowed_executables: Sequence[str | os.PathLike[str]],
        max_output_bytes: int = 256_000,
    ) -> None:
        root = Path(working_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("working_root must be a directory")
        if not allowed_executables:
            raise ValueError("at least one allowed executable is required")
        allowed: set[str] = set()
        for item in allowed_executables:
            executable = Path(item).resolve(strict=True)
            if not executable.is_file():
                raise ValueError("allowed executable must be an existing file")
            allowed.add(os.path.normcase(str(executable)))
        if isinstance(max_output_bytes, bool) or not isinstance(max_output_bytes, int) or max_output_bytes < 1:
            raise ValueError("max_output_bytes must be positive")
        self._root = root
        self._allowed = frozenset(allowed)
        self._max_output_bytes = max_output_bytes
        self._lock = threading.RLock()
        self._processes: dict[str, subprocess.Popen[bytes]] = {}
        self._jobs: dict[str, WindowsJob] = {}
        self._cancelled: set[str] = set()

    @property
    def active_worker_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._processes))

    def run(self, spec: WorkerSpec) -> WorkerResult:
        executable = Path(spec.executable).resolve(strict=True)
        if os.path.normcase(str(executable)) not in self._allowed:
            raise PermissionError("executable is not allow-listed")
        if not executable.is_file():
            raise ValueError("executable must be a file")
        cwd = (self._root / spec.working_directory).resolve(strict=True)
        if not cwd.is_dir() or not cwd.is_relative_to(self._root):
            raise PermissionError("working directory must remain beneath working_root")
        command = [str(executable), *spec.arguments]
        creation: dict[str, object] = {}
        if os.name == "nt":
            creation["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_SUSPENDED
            )
        else:
            creation["start_new_session"] = True
        started = time.monotonic()

        # Serialize ID reservation and process creation. On Windows the
        # primary thread remains suspended until Job Object assignment succeeds.
        with self._lock:
            if spec.worker_id in self._processes:
                raise RuntimeError(f"worker already running: {spec.worker_id}")
            job = WindowsJob() if os.name == "nt" else None
            process: subprocess.Popen[bytes] | None = None
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(cwd),
                    env=dict(spec.environment),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False,
                    close_fds=True,
                    **creation,
                )
                if job is not None:
                    job.assign_suspended(process)
            except Exception:
                if process is not None and process.poll() is None:
                    try:
                        if job is not None:
                            job.terminate()
                        process.kill()
                    finally:
                        process.wait()
                if job is not None:
                    job.close()
                raise
            self._processes[spec.worker_id] = process
            if job is not None:
                self._jobs[spec.worker_id] = job
            self._cancelled.discard(spec.worker_id)

        output: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
        truncated = threading.Event()

        def drain(name: str, pipe: object) -> None:
            while True:
                chunk = pipe.read(8192)
                if not chunk:
                    return
                remaining = self._max_output_bytes - len(output[name])
                if remaining > 0:
                    output[name].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated.set()

        readers = [
            threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
            threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
        ]
        timed_out = False
        cancelled = False
        try:
            for reader in readers:
                reader.start()
            try:
                process.wait(timeout=spec.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                self._terminate_process(process, spec.terminate_grace_seconds, job)
            if not timed_out and job is not None and not job.wait_empty(spec.terminate_grace_seconds):
                # A successful root process is not complete while descendants
                # remain in its private Job Object. Stop the remaining tree.
                self._terminate_process(process, spec.terminate_grace_seconds, job)

            # A child may exit while a descendant keeps an inherited pipe
            # open. On POSIX, terminate the process group (not merely the
            # already-exited leader) before waiting indefinitely on readers.
            for reader in readers:
                reader.join(timeout=max(0.1, spec.terminate_grace_seconds + 0.1))
            if any(reader.is_alive() for reader in readers):
                self._terminate_process(process, spec.terminate_grace_seconds, job)
                for reader in readers:
                    reader.join(timeout=max(1.0, spec.terminate_grace_seconds + 1.0))

            with self._lock:
                cancelled = spec.worker_id in self._cancelled
            return WorkerResult(
                worker_id=spec.worker_id,
                exit_code=process.poll(),
                timed_out=timed_out,
                cancelled=cancelled,
                duration_seconds=max(0.0, time.monotonic() - started),
                stdout=bytes(output["stdout"]).decode("utf-8", errors="replace"),
                stderr=bytes(output["stderr"]).decode("utf-8", errors="replace"),
                output_truncated=truncated.is_set(),
            )
        finally:
            # Do not leave a worker or descendant running if reader startup or
            # cleanup fails. Keep the Job Object alive until the tree is empty.
            if job is not None:
                if process.poll() is None or job.active_processes:
                    self._terminate_process(process, spec.terminate_grace_seconds, job)
                if not job.wait_empty(max(2.0, spec.terminate_grace_seconds + 1.0)):
                    job.close()  # kill-on-close is the final cleanup backstop
                    raise RuntimeError("Windows worker process tree did not become empty")
                job.close()
            elif process.poll() is None:
                self._terminate_process(process, spec.terminate_grace_seconds)
            # Registry cleanup is unconditional, including reader/pipe errors.
            with self._lock:
                self._processes.pop(spec.worker_id, None)
                self._jobs.pop(spec.worker_id, None)
                self._cancelled.discard(spec.worker_id)
            for pipe in (process.stdout, process.stderr):
                if pipe is not None:
                    pipe.close()

    def cancel(self, worker_id: str, *, grace_seconds: float = 1.0) -> bool:
        if isinstance(grace_seconds, bool) or not isinstance(grace_seconds, (int, float)) or not math.isfinite(grace_seconds) or grace_seconds < 0:
            raise ValueError("grace_seconds must be finite and non-negative")
        with self._lock:
            process = self._processes.get(worker_id)
            if process is None:
                return False
            job = self._jobs.get(worker_id)
            self._cancelled.add(worker_id)
        # The leader may already have exited while descendants remain in its
        # Job Object. Cancellation targets the whole registered worker tree.
        self._terminate_process(process, grace_seconds, job)
        return True

    @staticmethod
    def _terminate_process(
        process: subprocess.Popen[bytes],
        grace_seconds: float,
        job: WindowsJob | None = None,
    ) -> None:
        if os.name == "nt":
            if job is None:
                raise RuntimeError("Windows worker is missing its Job Object")
            job.terminate()
            if process.poll() is None:
                try:
                    process.wait(timeout=grace_seconds)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if not job.wait_empty(max(2.0, grace_seconds + 1.0)):
                raise RuntimeError("Windows Job Object still contains active processes")
            return

        # Signal the group even when the group leader has already exited:
        # descendants can still be alive and hold stdout/stderr descriptors.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        if process.poll() is None:
            try:
                process.wait(timeout=grace_seconds)
            except subprocess.TimeoutExpired:
                pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if process.poll() is None:
            process.wait()
