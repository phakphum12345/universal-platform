import sys
import threading
import time

import pytest

from universal_platform.runtime.supervisor import (
    PythonProcessSupervisor,
    WorkerResult,
    WorkerSpec,
    WorkerTerminationError,
)
from universal_platform.runtime.worker_ipc import WorkerIPCClient, WorkerIPCError
from universal_platform.runtime.worker_protocol import WorkerFrame, WorkerProtocolError, encode_frame


@pytest.fixture
def supervisor(tmp_path):
    return PythonProcessSupervisor(
        working_root=tmp_path,
        allowed_executables=(sys.executable,),
        max_output_bytes=4096,
    )


def worker_spec():
    return WorkerSpec(
        "template",
        sys.executable,
        ("-c", "pass"),
        working_directory=".",
        timeout_seconds=3,
    )


def test_worker_ipc_client_runs_one_shot_request_response(supervisor):
    script = (
        "import sys; "
        "from universal_platform.runtime.worker_protocol import read_frame, write_frame, WorkerFrame; "
        "request = read_frame(sys.stdin.buffer); "
        "write_frame(sys.stdout.buffer, WorkerFrame('RESPONSE', request.request_id, {'accepted': True}))"
    )
    client = WorkerIPCClient(
        supervisor,
        WorkerSpec("template", sys.executable, ("-c", script), timeout_seconds=3),
    )
    response = client.request(WorkerFrame("REQUEST", "request-1", {"operation": "test"}))
    assert response.message_type == "RESPONSE"
    assert response.request_id == "request-1"
    assert response.payload == {"accepted": True}
    assert supervisor.active_worker_ids == ()


def test_worker_ipc_client_rejects_non_request_frame(supervisor):
    client = WorkerIPCClient(supervisor, worker_spec())
    with pytest.raises(WorkerIPCError) as error:
        client.request(WorkerFrame("CANCEL", "request-2", {}))
    assert error.value.code == "worker.invalid_request_type"


class StubSupervisor:
    def __init__(self, result):
        self.result = result
        self.cancelled = []

    def run(self, spec):
        self.spec = spec
        return self.result

    def cancel(self, request_id, *, grace_seconds=1.0):
        self.cancelled.append((request_id, grace_seconds))
        return True


def worker_result(stdout_bytes=b"", *, exit_code=0, timed_out=False,
                  cancelled=False, output_truncated=False):
    return WorkerResult(
        worker_id="request-3",
        exit_code=exit_code,
        timed_out=timed_out,
        cancelled=cancelled,
        duration_seconds=0.01,
        stdout=stdout_bytes.decode("utf-8", errors="replace"),
        stderr="",
        output_truncated=output_truncated,
        stdout_bytes=stdout_bytes,
    )


def test_worker_ipc_client_uses_request_id_and_exact_framed_stdin():
    request = WorkerFrame("REQUEST", "request-3", {"value": 4})
    response_bytes = encode_frame(WorkerFrame("RESPONSE", "request-3", {"value": 8}))
    stub = StubSupervisor(worker_result(response_bytes))
    client = WorkerIPCClient(stub, worker_spec())
    response = client.request(request)
    assert response.payload == {"value": 8}
    assert stub.spec.worker_id.startswith("worker-")
    assert stub.spec.worker_id != "request-3"
    assert stub.spec.stdin_data == encode_frame(request)


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (WorkerFrame("RESPONSE", "other-id", {}), "worker.response_correlation_mismatch"),
        (WorkerFrame("CANCEL", "request-3", {}), "worker.response_type_mismatch"),
    ],
)
def test_worker_ipc_client_rejects_wrong_response_type_or_correlation(response, code):
    stub = StubSupervisor(worker_result(encode_frame(response)))
    client = WorkerIPCClient(stub, worker_spec())
    with pytest.raises(WorkerIPCError) as error:
        client.request(WorkerFrame("REQUEST", "request-3", {}))
    assert error.value.code == code


def test_worker_ipc_client_rejects_trailing_response_bytes():
    response = encode_frame(WorkerFrame("RESPONSE", "request-3", {})) + b"unexpected"
    client = WorkerIPCClient(StubSupervisor(worker_result(response)), worker_spec())
    with pytest.raises(WorkerIPCError) as error:
        client.request(WorkerFrame("REQUEST", "request-3", {}))
    assert error.value.code == "worker.response_trailing_data"


def test_worker_ipc_client_rejects_truncated_response():
    client = WorkerIPCClient(StubSupervisor(worker_result(b"\x00\x00")), worker_spec())
    with pytest.raises(WorkerIPCError) as error:
        client.request(WorkerFrame("REQUEST", "request-3", {}))
    assert error.value.code == "worker.response_invalid"


@pytest.mark.parametrize(
    ("result", "code"),
    [
        (worker_result(exit_code=1), "worker.nonzero_exit"),
        (worker_result(timed_out=True, exit_code=-9), "worker.timeout"),
        (worker_result(cancelled=True, exit_code=-9), "worker.cancelled"),
        (worker_result(encode_frame(WorkerFrame("RESPONSE", "request-3", {})),
                       output_truncated=True), "worker.response_truncated"),
    ],
)
def test_worker_ipc_client_maps_supervisor_terminal_states(result, code):
    client = WorkerIPCClient(StubSupervisor(result), worker_spec())
    with pytest.raises(WorkerIPCError) as error:
        client.request(WorkerFrame("REQUEST", "request-3", {}))
    assert error.value.code == code


def test_worker_ipc_client_exposes_unconfirmed_process_tree_termination():
    class UnconfirmedSupervisor:
        def run(self, spec):
            raise WorkerTerminationError(spec.worker_id)

        def cancel(self, request_id, *, grace_seconds=1.0):
            return False

    client = WorkerIPCClient(UnconfirmedSupervisor(), worker_spec())
    with pytest.raises(WorkerIPCError) as error:
        client.request(WorkerFrame("REQUEST", "request-3", {}))
    assert error.value.code == "worker.termination_unconfirmed"
    assert error.value.termination_confirmed is False


def test_worker_ipc_client_cancel_retries_across_worker_startup_race():
    started = threading.Event()
    cancelled = threading.Event()

    class DelayedSupervisor:
        def run(self, spec):
            time.sleep(0.1)
            started.set()
            assert cancelled.wait(timeout=2)
            return worker_result(cancelled=True, exit_code=-9)

        def cancel(self, request_id, *, grace_seconds=1.0):
            if not started.is_set():
                return False
            cancelled.set()
            return True

    client = WorkerIPCClient(DelayedSupervisor(), worker_spec())
    errors = []

    def invoke():
        try:
            client.request(WorkerFrame("REQUEST", "request-3", {}))
        except WorkerIPCError as error:
            errors.append(error)

    thread = threading.Thread(target=invoke)
    thread.start()
    assert client.cancel("request-3", grace_seconds=0.2)
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert errors[0].code == "worker.cancelled"


def test_worker_ipc_client_rejects_invalid_cancel_id(supervisor):
    client = WorkerIPCClient(supervisor, worker_spec())
    with pytest.raises(ValueError, match="request_id"):
        client.cancel("bad\x00id")


def test_worker_ipc_client_rejects_template_with_preloaded_stdin(supervisor):
    template = WorkerSpec("template", sys.executable, stdin_data=b"unexpected")
    with pytest.raises(ValueError, match="template"):
        WorkerIPCClient(supervisor, template)


def test_worker_ipc_client_accounts_for_four_byte_frame_header():
    class LimitedSupervisor(StubSupervisor):
        max_input_bytes = 64

    response = encode_frame(WorkerFrame("RESPONSE", "request-3", {"ok": True}))
    stub = LimitedSupervisor(worker_result(response))
    client = WorkerIPCClient(stub, worker_spec(), max_frame_bytes=1024)
    client.request(WorkerFrame("REQUEST", "request-3", {"x": 1}))
    assert len(stub.spec.stdin_data) <= stub.max_input_bytes
    assert client._max_frame_bytes == stub.max_input_bytes - 4


def test_worker_ipc_client_rejects_oversized_frame_before_supervisor():
    class LimitedSupervisor(StubSupervisor):
        max_input_bytes = 64

    stub = LimitedSupervisor(worker_result())
    client = WorkerIPCClient(stub, worker_spec(), max_frame_bytes=1024)
    with pytest.raises(WorkerIPCError) as error:
        client.request(WorkerFrame("REQUEST", "request-3", {"data": "x" * 200}))
    assert error.value.code == "worker.request_invalid"
    assert not hasattr(stub, "spec")


def test_worker_frame_rejects_nul_request_id():
    with pytest.raises(WorkerProtocolError, match="NUL-free"):
        WorkerFrame("REQUEST", "bad\x00id", {})


def test_worker_ipc_client_rejects_duplicate_active_request_id_before_second_launch():
    started = threading.Event()
    release = threading.Event()
    calls = []

    class BlockingSupervisor:
        def run(self, spec):
            calls.append(spec)
            started.set()
            assert release.wait(timeout=2)
            return worker_result(cancelled=True, exit_code=-9)

        def cancel(self, worker_id, *, grace_seconds=1.0):
            assert worker_id == calls[0].worker_id
            release.set()
            return True

    client = WorkerIPCClient(BlockingSupervisor(), worker_spec())
    errors = []

    def invoke():
        try:
            client.request(WorkerFrame("REQUEST", "same-request", {}))
        except WorkerIPCError as error:
            errors.append(error)

    thread = threading.Thread(target=invoke)
    thread.start()
    assert started.wait(timeout=2)
    with pytest.raises(WorkerIPCError) as duplicate:
        client.request(WorkerFrame("REQUEST", "same-request", {}))
    assert duplicate.value.code == "worker.request_already_active"
    assert duplicate.value.termination_confirmed is True
    assert len(calls) == 1
    assert client.cancel("same-request", grace_seconds=0.1)
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert errors[0].code == "worker.cancelled"
