import os
import sys
from types import SimpleNamespace

import pytest

from universal_platform.runtime.process_identity import (
    ProcessIdentity,
    capture_process_identity,
)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs identity")
def test_linux_process_identity_captures_creation_and_process_tree_tokens():
    identity = capture_process_identity(
        SimpleNamespace(pid=os.getpid()),
        worker_id="worker-test",
        host_instance_id="host-test",
    )
    assert identity.platform == "linux"
    assert identity.pid == os.getpid()
    assert identity.creation_token.isdigit()
    assert identity.host_boot_id
    assert identity.process_group_id == os.getpgrp()
    assert identity.session_id == os.getsid(0)
    assert identity.to_dict()["worker_id"] == "worker-test"


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs identity")
def test_linux_process_identity_uses_starttime_after_parenthesized_comm(tmp_path):
    proc_root = tmp_path
    process_dir = proc_root / "123"
    process_dir.mkdir()
    fields = ["S", "1", "123", "123"] + ["0"] * 15 + ["98765"]
    (process_dir / "stat").write_text(
        "123 (worker name (with parens)) " + " ".join(fields),
        encoding="ascii",
    )
    boot = proc_root / "sys/kernel/random"
    boot.mkdir(parents=True)
    (boot / "boot_id").write_text("boot-token\n", encoding="ascii")

    identity = capture_process_identity(
        SimpleNamespace(pid=123),
        worker_id="worker-123",
        host_instance_id="host-123",
        proc_root=proc_root,
    )
    assert identity.creation_token == "98765"
    assert identity.process_group_id == 123
    assert identity.session_id == 123
    assert identity.host_boot_id == "boot-token"


@pytest.mark.skipif(sys.platform != "linux", reason="Linux procfs identity")
@pytest.mark.parametrize("state", ["Z", "X"])
def test_linux_process_identity_rejects_zombie_or_dead_process(tmp_path, state):
    process_dir = tmp_path / "321"
    process_dir.mkdir()
    fields = [state, "1", "321", "321"] + ["0"] * 15 + ["12345"]
    (process_dir / "stat").write_text(
        "321 (worker) " + " ".join(fields), encoding="ascii"
    )
    boot = tmp_path / "sys/kernel/random"
    boot.mkdir(parents=True)
    (boot / "boot_id").write_text("boot-token", encoding="ascii")
    with pytest.raises(ProcessLookupError):
        capture_process_identity(
            SimpleNamespace(pid=321),
            worker_id="worker-321",
            host_instance_id="host-321",
            proc_root=tmp_path,
        )


def test_process_identity_rejects_pid_only_or_invalid_identity_fields():
    with pytest.raises(ValueError, match="creation_token"):
        ProcessIdentity(
            platform="linux",
            pid=1,
            creation_token="",
            host_boot_id="boot",
            worker_id="worker",
            host_instance_id="host",
            process_group_id=1,
            session_id=1,
        )
    with pytest.raises(ValueError, match="positive integer"):
        ProcessIdentity(
            platform="linux",
            pid=0,
            creation_token="1",
            host_boot_id="boot",
            worker_id="worker",
            host_instance_id="host",
            process_group_id=1,
            session_id=1,
        )


def test_process_identity_rejects_unsupported_platform():
    with pytest.raises(ValueError, match="unsupported"):
        ProcessIdentity(
            platform="darwin",
            pid=1,
            creation_token="1",
            host_boot_id=None,
            worker_id="worker",
            host_instance_id="host",
        )
