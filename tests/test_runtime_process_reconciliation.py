import os
from pathlib import Path
import subprocess
import sys

import pytest

from universal_platform.runtime.process_identity import ProcessIdentity
from universal_platform.runtime.process_reconciliation import (
    ProcessIdentityInspector,
    ProcessLiveness,
)
from universal_platform.runtime.windows_job import WindowsJob


def linux_identity(*, pid=101, start="900", boot="boot-token"):
    return ProcessIdentity(
        platform="linux",
        pid=pid,
        creation_token=start,
        host_boot_id=boot,
        worker_id="worker-101",
        host_instance_id="host-101",
        process_group_id=pid,
        session_id=pid,
    )


def write_boot_id(root: Path, value="boot-token"):
    path = root / "sys" / "kernel" / "random"
    path.mkdir(parents=True)
    (path / "boot_id").write_text(value + "\n", encoding="ascii")


def write_proc_stat(root: Path, pid, *, state="S", pgrp=None, session=None, start=900):
    process = root / str(pid)
    process.mkdir()
    fields = [
        state,
        "1",
        str(pid if pgrp is None else pgrp),
        str(pid if session is None else session),
    ] + ["0"] * 15 + [str(start)]
    (process / "stat").write_text(
        f"{pid} (worker with (parenthesized) comm) " + " ".join(fields),
        encoding="ascii",
    )


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs process reconciliation")
def test_linux_inspector_matches_leader_pid_and_starttime(tmp_path):
    write_boot_id(tmp_path)
    write_proc_stat(tmp_path, 101, start=900)
    evidence = ProcessIdentityInspector(proc_root=tmp_path).inspect(linux_identity())
    assert evidence.status is ProcessLiveness.PRESENT
    assert evidence.method == "linux.procfs.boot-id-starttime-pgrp-session"
    assert "leader-pid-and-starttime-match" in evidence.details
    assert evidence.to_dict()["process_identity"]["pid"] == 101


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs process reconciliation")
def test_linux_inspector_finds_descendant_when_original_leader_has_exited(tmp_path):
    write_boot_id(tmp_path)
    write_proc_stat(tmp_path, 202, pgrp=101, session=101, start=500)
    evidence = ProcessIdentityInspector(proc_root=tmp_path).inspect(linux_identity())
    assert evidence.status is ProcessLiveness.PRESENT
    assert "original-process-group-has-live-member" in evidence.details


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs process reconciliation")
def test_linux_inspector_treats_reused_leader_pid_as_absent(tmp_path):
    write_boot_id(tmp_path)
    write_proc_stat(tmp_path, 101, pgrp=101, session=101, start=901)
    evidence = ProcessIdentityInspector(proc_root=tmp_path).inspect(linux_identity())
    assert evidence.status is ProcessLiveness.ABSENT
    assert "PID was reused" not in (evidence.reason or "")


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs process reconciliation")
def test_linux_inspector_fails_closed_when_reused_pid_and_group_are_ambiguous(tmp_path):
    write_boot_id(tmp_path)
    write_proc_stat(tmp_path, 101, pgrp=101, session=101, start=901)
    write_proc_stat(tmp_path, 202, pgrp=101, session=101, start=500)
    evidence = ProcessIdentityInspector(proc_root=tmp_path).inspect(linux_identity())
    assert evidence.status is ProcessLiveness.UNKNOWN
    assert "reused" in (evidence.reason or "")


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs process reconciliation")
def test_linux_inspector_reports_absent_when_process_group_is_empty(tmp_path):
    write_boot_id(tmp_path)
    evidence = ProcessIdentityInspector(proc_root=tmp_path).inspect(linux_identity())
    assert evidence.status is ProcessLiveness.ABSENT


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs process reconciliation")
def test_linux_inspector_uses_boot_id_to_reject_previous_boot_processes(tmp_path):
    write_boot_id(tmp_path, "current-boot")
    evidence = ProcessIdentityInspector(proc_root=tmp_path).inspect(linux_identity(boot="previous-boot"))
    assert evidence.status is ProcessLiveness.ABSENT
    assert "boot ID changed" in (evidence.reason or "")


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs process reconciliation")
def test_linux_inspector_reports_unknown_for_unparseable_proc_entries(tmp_path):
    write_boot_id(tmp_path)
    process = tmp_path / "777"
    process.mkdir()
    (process / "stat").write_text("malformed proc record", encoding="ascii")
    evidence = ProcessIdentityInspector(proc_root=tmp_path).inspect(linux_identity())
    assert evidence.status is ProcessLiveness.UNKNOWN
    assert "could not be inspected" in (evidence.reason or "")


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs process reconciliation")
def test_linux_inspector_ignores_zombie_processes(tmp_path):
    write_boot_id(tmp_path)
    write_proc_stat(tmp_path, 101, state="Z", start=900)
    evidence = ProcessIdentityInspector(proc_root=tmp_path).inspect(linux_identity())
    assert evidence.status is ProcessLiveness.ABSENT


def test_inspector_does_not_claim_windows_identity_present_on_non_windows_host():
    identity = ProcessIdentity(
        platform="windows",
        pid=123,
        creation_token="0000000000000001",
        host_boot_id=None,
        worker_id="worker-windows",
        host_instance_id="host-windows",
        job_object_id="Local\\UniversalPlatform-test",
    )
    evidence = ProcessIdentityInspector().inspect(identity)
    if os.name != "nt":
        assert evidence.status is ProcessLiveness.UNKNOWN


@pytest.mark.skipif(os.name != "nt", reason="Windows named Job Object process reconciliation")
def test_windows_inspector_queries_named_job_process_tree_liveness():
    job = WindowsJob()
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000004,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        job.assign_suspended(process)
        identity = ProcessIdentity(
            platform="windows",
            pid=process.pid,
            creation_token="0000000000000001",
            host_boot_id=None,
            worker_id="worker-windows",
            host_instance_id="host-windows",
            job_object_id=job.object_id,
        )
        inspector = ProcessIdentityInspector()
        assert inspector.inspect(identity).status is ProcessLiveness.PRESENT
        job.terminate()
        process.wait(timeout=5)
        assert inspector.inspect(identity).status is ProcessLiveness.ABSENT
    finally:
        if process.poll() is None:
            job.terminate()
            process.wait(timeout=5)
        job.close()


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs process reconciliation")
def test_linux_inspector_returns_unknown_for_identity_without_group_leader_anchor(tmp_path):
    identity = ProcessIdentity(
        platform="linux",
        pid=101,
        creation_token="900",
        host_boot_id="boot-token",
        worker_id="worker-101",
        host_instance_id="host-101",
        process_group_id=99,
        session_id=99,
    )
    evidence = ProcessIdentityInspector(proc_root=tmp_path).inspect(identity)
    assert evidence.status is ProcessLiveness.UNKNOWN
    assert "not its process-group and session leader" in (evidence.reason or "")
