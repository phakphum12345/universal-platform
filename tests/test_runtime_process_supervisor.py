import os
from pathlib import Path
import sys
import threading
import time

import pytest

from universal_platform.runtime.supervisor import PythonProcessSupervisor, WorkerSpec


@pytest.fixture
def supervisor(tmp_path):
    return PythonProcessSupervisor(
        working_root=tmp_path,
        allowed_executables=(sys.executable,),
        max_output_bytes=64,
    )


def test_supervisor_runs_allowlisted_python_without_shell(supervisor, tmp_path):
    result = supervisor.run(WorkerSpec(
        "worker-a", sys.executable, ("-c", "print('worker-ok')"),
        working_directory=".", environment={}, timeout_seconds=3,
    ))
    assert result.exit_code == 0
    assert result.stdout.strip() == "worker-ok"
    assert not result.timed_out and not result.cancelled
    assert supervisor.active_worker_ids == ()


def test_supervisor_rejects_unlisted_executable(supervisor, tmp_path):
    other = tmp_path / "not-allowed"
    other.write_text("not executable", encoding="utf-8")
    with pytest.raises(PermissionError, match="allow-listed"):
        supervisor.run(WorkerSpec("bad", str(other)))


def test_supervisor_rejects_working_directory_escape(supervisor, tmp_path):
    outside = tmp_path.parent / "outside"
    outside.mkdir()
    with pytest.raises(PermissionError, match="beneath"):
        supervisor.run(WorkerSpec("escape", sys.executable, ("-c", "pass"), ".."))


def test_supervisor_bounds_captured_output(supervisor):
    result = supervisor.run(WorkerSpec(
        "noisy", sys.executable, ("-c", "print('x' * 1000)"),
        timeout_seconds=3,
    ))
    assert result.exit_code == 0
    assert len(result.stdout.encode("utf-8")) <= 64
    assert result.output_truncated


def test_supervisor_terminates_timed_out_worker(supervisor):
    result = supervisor.run(WorkerSpec(
        "timeout", sys.executable, ("-c", "import time; time.sleep(5)"),
        timeout_seconds=0.1, terminate_grace_seconds=0.1,
    ))
    assert result.timed_out
    assert result.exit_code is not None
    assert "timeout" not in supervisor.active_worker_ids


def test_supervisor_supports_external_cancellation(supervisor):
    results = []
    thread = threading.Thread(target=lambda: results.append(supervisor.run(WorkerSpec(
        "cancel-me", sys.executable, ("-c", "import time; time.sleep(5)"),
        timeout_seconds=10, terminate_grace_seconds=0.1,
    ))))
    thread.start()
    deadline = time.monotonic() + 3
    while "cancel-me" not in supervisor.active_worker_ids and time.monotonic() < deadline:
        time.sleep(0.01)
    assert "cancel-me" in supervisor.active_worker_ids
    assert supervisor.cancel("cancel-me", grace_seconds=0.1)
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert results[0].cancelled
    assert results[0].exit_code is not None


def test_supervisor_rejects_invalid_limits(tmp_path):
    with pytest.raises(ValueError, match="max_output_bytes"):
        PythonProcessSupervisor(working_root=tmp_path, allowed_executables=(sys.executable,), max_output_bytes=0)
    with pytest.raises(ValueError, match="timeout_seconds"):
        WorkerSpec("invalid", sys.executable, timeout_seconds=0)
