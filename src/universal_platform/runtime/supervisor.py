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
    stdin_data: bytes | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.worker_id, str) or not self.worker_id.strip() or "\x00" in self.worker_id:
            raise ValueError("worker_id must be a non-empty NUL-free string")
        if not isinstance(self.executable, str) or not self.executable.strip() or "\x00" in self.executable:
            raise ValueError("executable must be a non-empty NUL-free string")
        if not isinstance(self.arguments, tuple):
            raise ValueError("arguments must be an immutable tuple")
        if any(not isinstance(item, str) or "\x00" in item for item in self.arguments):
            raise ValueError("arguments must be NUL-free strings")
        if not isinstance(self.working_directory, str) or not self.working_directory.strip() or "\x00" in self.working_directory:
            raise ValueError("working_directory must be a non-empty NUL-free string")
        if not isinstance(self.environment, Mapping):
            raise ValueError("environment must be a mapping of string names to values")
        if self.stdin_data is not None and not isinstance(self.stdin_data, bytes):
            raise ValueError("stdin_data must be bytes or None")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)) or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if isinstance(self.terminate_grace_seconds, bool) or not isinstance(self.terminate_grace_seconds, (int, float)) or not math.isfinite(self.terminate_grace_seconds) or self.terminate_grace_seconds < 0:
            raise ValueError("terminate_grace_seconds must be finite and non-negative")
        for key, value in self.environment.items():
            if not isinstance(key, str) or not isinstance(value, str) or not key or "=" in key or "\x00" in key or "\x00" in value:
                raise ValueError("environment entries must have valid names and NUL-free string values")


class WorkerTerminationError(RuntimeError):
    """Raised when the supervisor cannot confirm the worker tree has stopped."""

    def __init__(self, worker_id: str, message: str = "worker process-tree termination could not be confirmed"):
        self.worker_id = worker_id
        self.termination_confirmed = False
        super().__init__(message)


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
    stdout_bytes: bytes = b""


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
        max_input_bytes: int = 1_048_576,
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
        if isinstance(max_input_bytes, bool) or not isinstance(max_input_bytes, int) or max_input_bytes < 1:
            raise ValueError("max_input_bytes must be positive")
        self._root = root
        self._allowed = frozenset(allowed)
        self._max_output_bytes = max_output_bytes
        self._max_input_bytes = max_input_bytes
        self._lock = threading.RLock()
        self._processes: dict[str, subprocess.Popen[bytes]] = {}
        self._jobs: dict[str, WindowsJob] = {}
        self._starting: set[str] = set()
        self._cancelled: set[str] = set()

    @property
    def active_worker_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._processes))

    @property
    def max_input_bytes(self) -> int:
        """Maximum raw stdin buffer size accepted by this supervisor."""
        return self._max_input_bytes

    def run(self, spec: WorkerSpec) -> WorkerResult:
        executable = Path(spec.executable).resolve(strict=True)
        if os.path.normcase(str(executable)) not in self._allowed:
            raise PermissionError("executable is not allow-listed")
        if not executable.is_file():
            raise ValueError("executable must be a file")
        if spec.stdin_data is not None and memoryview(spec.stdin_data).nbytes > self._max_input_bytes:
            raise ValueError("worker stdin payload exceeds max_input_bytes")
        cwd = (self._root / spec.working_directory).resolve(strict=True)
        if not cwd.is_dir() or not cwd.is_relative_to(self._root):
            raise PermissionError("working directory must remain beneath working_root")
        command = [str(executable), *spec.arguments]
        creation: dict[str, object] = {}
        if os.name == "nt":
            creation["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000004  # CREATE_SUSPENDED
            )
        else:
            creation["start_new_session"] = True
        started = time.monotonic()

        # Reserve the ID under lock, but do not hold the registry lock while
        # the OS creates the process. Cancellation can mark a starting worker.
        with self._lock:
            if spec.worker_id in self._processes or spec.worker_id in self._starting:
                raise RuntimeError(f"worker already running: {spec.worker_id}")
            self._starting.add(spec.worker_id)
        job = None
        process: subprocess.Popen[bytes] | None = None
        try:
            if os.name == "nt":
                job = WindowsJob()
            process = subprocess.Popen(
                command,
                cwd=str(cwd),
                env=dict(spec.environment),
                stdin=subprocess.PIPE if spec.stdin_data is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                close_fds=True,
                **creation,
            )
            if job is not None:
                job.assign_suspended(process)
        except Exception as launch_error:
            cleanup_error: Exception | None = None
            if process is not None and process.poll() is None:
                if job is not None:
                    try:
                        job.terminate()
                    except Exception as error:
                        cleanup_error = error
                try:
                    process.kill()
                except OSError as error:
                    if process.poll() is None:
                        cleanup_error = cleanup_error or error
                try:
                    process.wait(timeout=max(1.0, spec.terminate_grace_seconds + 1.0))
                except Exception as error:
                    cleanup_error = cleanup_error or error
            if job is not None:
                try:
                    job.close()
                except Exception as error:
                    cleanup_error = cleanup_error or error
            with self._lock:
                self._starting.discard(spec.worker_id)
                self._cancelled.discard(spec.worker_id)
            if cleanup_error is not None and process is not None:
                raise WorkerTerminationError(spec.worker_id) from cleanup_error
            raise launch_error
        with self._lock:
            self._processes[spec.worker_id] = process
            self._starting.discard(spec.worker_id)
            if job is not None:
                self._jobs[spec.worker_id] = job
            cancel_requested_before_start = spec.worker_id in self._cancelled

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
        input_errors: list[BaseException] = []
        writer: threading.Thread | None = None
        if spec.stdin_data is not None:
            def write_input() -> None:
                try:
                    view = memoryview(spec.stdin_data)
                    offset = 0
                    while offset < len(view):
                        written = os.write(process.stdin.fileno(), view[offset:])
                        if written <= 0:
                            raise BrokenPipeError("worker stdin closed before the request was written")
                        offset += written
                except (BrokenPipeError, OSError, ValueError) as error:
                    input_errors.append(error)
                finally:
                    if process.stdin is not None:
                        try:
                            process.stdin.close()
                        except (OSError, ValueError) as error:
                            input_errors.append(error)

            writer = threading.Thread(target=write_input, daemon=True)
        timed_out = False
        cancelled = False
        try:
            for reader in readers:
                reader.start()
            if writer is not None:
                writer.start()
            if cancel_requested_before_start:
                cancelled = True
                self._terminate_process(process, spec.terminate_grace_seconds, job)
            else:
                try:
                    process.wait(timeout=spec.timeout_seconds)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    self._terminate_process(process, spec.terminate_grace_seconds, job)
            if writer is not None:
                writer.join(timeout=max(0.1, spec.terminate_grace_seconds + 0.1))
                if writer.is_alive():
                    self._terminate_process(process, spec.terminate_grace_seconds, job)
                    writer.join(timeout=max(1.0, spec.terminate_grace_seconds + 1.0))
                    if writer.is_alive():
                        raise RuntimeError("worker stdin writer did not stop after process termination")
            if not timed_out and job is not None and not job.wait_empty(spec.terminate_grace_seconds):
                # A successful root process is not complete while descendants
                # remain in its private Job Object. Stop the remaining tree.
                self._terminate_process(process, spec.terminate_grace_seconds, job)
            elif not timed_out and job is None and self._process_group_exists(process.pid):
                # POSIX descendants may close inherited pipes and outlive the
                # root. A clean reader join alone is not proof of tree exit.
                self._terminate_process(process, spec.terminate_grace_seconds)

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
            if input_errors and not timed_out and not cancelled:
                raise RuntimeError("worker stdin write failed") from input_errors[0]
            return WorkerResult(
                worker_id=spec.worker_id,
                exit_code=process.poll(),
                timed_out=timed_out,
                cancelled=cancelled,
                duration_seconds=max(0.0, time.monotonic() - started),
                stdout=bytes(output["stdout"]).decode("utf-8", errors="replace"),
                stderr=bytes(output["stderr"]).decode("utf-8", errors="replace"),
                output_truncated=truncated.is_set(),
                stdout_bytes=bytes(output["stdout"]),
            )
        finally:
            cleanup_error: Exception | None = None
            # Stop a blocked input writer before closing its process/Job handles.
            # On POSIX this also kills descendants that may still hold the pipe.
            if writer is not None and writer.is_alive():
                try:
                    self._terminate_process(process, spec.terminate_grace_seconds, job)
                except Exception as error:
                    cleanup_error = error
                finally:
                    writer.join(timeout=max(1.0, spec.terminate_grace_seconds + 1.0))
                    if writer.is_alive():
                        cleanup_error = cleanup_error or RuntimeError(
                            "worker stdin writer did not stop during cleanup"
                        )
            # Keep registry cleanup unconditional even if the OS refuses to
            # confirm termination. Closing the Job Object remains kill-on-close.
            try:
                if job is not None:
                    try:
                        if process.poll() is None or job.active_processes:
                            self._terminate_process(process, spec.terminate_grace_seconds, job)
                        if not job.wait_empty(max(2.0, spec.terminate_grace_seconds + 1.0)):
                            cleanup_error = RuntimeError(
                                "Windows worker process tree did not become empty"
                            )
                    except Exception as error:
                        cleanup_error = cleanup_error or error
                    finally:
                        try:
                            job.close()
                        except Exception as error:
                            cleanup_error = cleanup_error or error
                elif process.poll() is None or (
                    os.name != "nt" and self._process_group_exists(process.pid)
                ):
                    try:
                        self._terminate_process(process, spec.terminate_grace_seconds)
                    except Exception as error:
                        cleanup_error = cleanup_error or error
            finally:
                with self._lock:
                    self._processes.pop(spec.worker_id, None)
                    self._jobs.pop(spec.worker_id, None)
                    self._starting.discard(spec.worker_id)
                    self._cancelled.discard(spec.worker_id)
                for pipe in (process.stdin, process.stdout, process.stderr):
                    if pipe is not None and not pipe.closed:
                        pipe.close()
            if cleanup_error is not None:
                raise WorkerTerminationError(spec.worker_id) from cleanup_error

    def cancel(self, worker_id: str, *, grace_seconds: float = 1.0) -> bool:
        if isinstance(grace_seconds, bool) or not isinstance(grace_seconds, (int, float)) or not math.isfinite(grace_seconds) or grace_seconds < 0:
            raise ValueError("grace_seconds must be finite and non-negative")
        with self._lock:
            process = self._processes.get(worker_id)
            if process is None:
                if worker_id in self._starting:
                    self._cancelled.add(worker_id)
                    return True
                return False
            job = self._jobs.get(worker_id)
            if process.poll() is not None:
                if job is not None:
                    try:
                        if job.active_processes == 0:
                            return False
                    except Exception:
                        # If the OS cannot report Job state, fail toward
                        # termination rather than assuming the tree is empty.
                        pass
                elif not self._process_group_exists(process.pid):
                    return False
            self._cancelled.add(worker_id)
        # The leader may already have exited while descendants remain in its
        # Job Object or POSIX process group. Cancellation targets the whole tree.
        self._terminate_process(process, grace_seconds, job)
        return True

    @staticmethod
    def _linux_process_group_has_live_members(
        process_group_id: int,
        proc_root: Path = Path("/proc"),
    ) -> bool | None:
        """Return whether /proc reports a live member; Z/X entries are terminated.

        None means /proc could not be inspected and the caller should fall back
        to the portable killpg probe.
        """
        try:
            entries = tuple(proc_root.iterdir())
        except OSError:
            return None
        for entry in entries:
            if not entry.name.isdigit():
                continue
            try:
                stat = (entry / "stat").read_text(encoding="ascii")
                closing = stat.rfind(")")
                if closing < 0:
                    continue
                fields = stat[closing + 2:].split()
                if len(fields) < 3:
                    continue
                state = fields[0]
                group_id = int(fields[2])
            except (OSError, ValueError, UnicodeError):
                continue
            if group_id == process_group_id and state not in {"Z", "X"}:
                return True
        return False

    @staticmethod
    def _process_group_exists(process_group_id: int) -> bool:
        if os.name == "nt":
            return False
        try:
            os.killpg(process_group_id, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        linux_live = PythonProcessSupervisor._linux_process_group_has_live_members(
            process_group_id
        )
        return linux_live if linux_live is not None else True

    @classmethod
    def _wait_process_group_empty(cls, process_group_id: int, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while cls._process_group_exists(process_group_id):
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)
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
        if not PythonProcessSupervisor._wait_process_group_empty(
            process.pid, max(1.0, grace_seconds + 1.0)
        ):
            raise RuntimeError("POSIX worker process group did not become empty")
