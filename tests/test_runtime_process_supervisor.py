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


def test_worker_spec_rejects_nonfinite_limits_and_invalid_environment():
    with pytest.raises(ValueError, match="finite and positive"):
        WorkerSpec("nan-timeout", sys.executable, timeout_seconds=float("nan"))
    with pytest.raises(ValueError, match="finite and non-negative"):
        WorkerSpec("infinite-grace", sys.executable, terminate_grace_seconds=float("inf"))
    with pytest.raises(ValueError, match="NUL-free"):
        WorkerSpec("nul-env", sys.executable, environment={"VALUE": "bad" + chr(0) + "value"})
    with pytest.raises(ValueError, match="string values"):
        WorkerSpec("bad-env-type", sys.executable, environment={"VALUE": 123})


@pytest.mark.skipif(os.name == "nt", reason="POSIX process groups are required for descendant cleanup")
def test_supervisor_cleans_descendants_that_keep_pipes_open_after_parent_exits(supervisor):
    child = "import time; time.sleep(30)"
    parent = (
        "import subprocess,sys; "
        f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
        "print('parent-exit')"
    )
    started = time.monotonic()
    result = supervisor.run(WorkerSpec(
        "orphan-pipe-holder", sys.executable, ("-c", parent),
        timeout_seconds=3, terminate_grace_seconds=0.1,
    ))
    assert result.exit_code == 0
    assert result.stdout.strip() == "parent-exit"
    assert time.monotonic() - started < 3
    assert supervisor.active_worker_ids == ()


def test_supervisor_rejects_duplicate_worker_id_without_spawning_second_process(supervisor):
    results = []
    first = threading.Thread(target=lambda: results.append(supervisor.run(WorkerSpec(
        "same-id", sys.executable, ("-c", "import time; time.sleep(0.3)"),
        timeout_seconds=3,
    ))))
    first.start()
    deadline = time.monotonic() + 3
    while "same-id" not in supervisor.active_worker_ids and time.monotonic() < deadline:
        time.sleep(0.01)
    assert "same-id" in supervisor.active_worker_ids
    with pytest.raises(RuntimeError, match="already running"):
        supervisor.run(WorkerSpec("same-id", sys.executable, ("-c", "print('duplicate')")))
    first.join(timeout=3)
    assert not first.is_alive()
    assert len(results) == 1
    assert results[0].exit_code == 0
    assert supervisor.active_worker_ids == ()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object containment requires Windows")
def test_windows_supervisor_terminates_descendants_after_parent_exits(supervisor, tmp_path):
    marker = tmp_path / "descendant-survived.txt"
    child = (
        "import time; from pathlib import Path; "
        f"time.sleep(0.6); Path({str(marker)!r}).write_text('survived')"
    )
    parent = (
        "import subprocess,sys; "
        f"subprocess.Popen([sys.executable, '-c', {child!r}]); "
        "print('parent-exit')"
    )
    started = time.monotonic()
    result = supervisor.run(WorkerSpec(
        "windows-descendant", sys.executable, ("-c", parent),
        timeout_seconds=3, terminate_grace_seconds=0.1,
    ))
    assert result.exit_code == 0
    assert result.stdout.strip() == "parent-exit"
    assert time.monotonic() - started < 3
    time.sleep(0.8)
    assert not marker.exists()
    assert supervisor.active_worker_ids == ()


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object containment requires Windows")
def test_windows_assignment_failure_never_resumes_worker(supervisor, tmp_path, monkeypatch):
    from universal_platform.runtime import windows_job

    marker = tmp_path / "worker-ran.txt"
    code = f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')"

    def reject_assignment(self, process):
        raise RuntimeError("injected Job Object assignment failure")

    monkeypatch.setattr(windows_job.WindowsJob, "assign_suspended", reject_assignment)
    with pytest.raises(RuntimeError, match="assignment failure"):
        supervisor.run(WorkerSpec(
            "assignment-failure", sys.executable, ("-c", code),
            timeout_seconds=3,
        ))
    time.sleep(0.2)
    assert not marker.exists()
    assert supervisor.active_worker_ids == ()
