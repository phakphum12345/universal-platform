"""One-shot request/response client for explicitly supervised trusted workers.

The host supplies the allow-listed WorkerSpec template. The client sends one
bounded REQUEST frame on stdin, requires exactly one correlated RESPONSE frame
on stdout, and delegates cancellation to the process supervisor. This is not
a persistent channel or a security sandbox.
"""
from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from io import BytesIO
from uuid import uuid4

from .process_identity import ProcessIdentity
from .supervisor import PythonProcessSupervisor, WorkerSpec, WorkerTerminationError
from .worker_protocol import (
    DEFAULT_MAX_FRAME_BYTES,
    WorkerFrame,
    WorkerProtocolError,
    encode_frame,
    read_frame,
)


class WorkerIPCError(RuntimeError):
    """A supervised worker request failed its transport or lifecycle contract."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        termination_confirmed: bool = True,
    ):
        self.code = code
        self.termination_confirmed = termination_confirmed
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class WorkerInvocationHandle:
    """Immutable cancellation identity reserved before a worker process starts."""

    request_id: str
    worker_id: str


class WorkerIPCClient:
    """Executes one framed request in one host-configured supervised process.

    The worker executable, arguments, working directory and environment are
    supplied by trusted host configuration, never by the request payload.
    """

    def __init__(
        self,
        supervisor: PythonProcessSupervisor,
        worker_spec: WorkerSpec,
        *,
        max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES,
    ) -> None:
        if not callable(getattr(supervisor, "run", None)) or not callable(
            getattr(supervisor, "cancel", None)
        ):
            raise TypeError("supervisor must provide run and cancel")
        if not isinstance(worker_spec, WorkerSpec):
            raise TypeError("worker_spec must be a WorkerSpec")
        if worker_spec.stdin_data is not None:
            raise ValueError("worker_spec template must not contain request stdin_data")
        if (
            isinstance(max_frame_bytes, bool)
            or not isinstance(max_frame_bytes, int)
            or not 1 <= max_frame_bytes <= 0xFFFFFFFF
        ):
            raise ValueError("max_frame_bytes must be a positive uint32 integer")
        supervisor_input_limit = getattr(supervisor, "max_input_bytes", None)
        if supervisor_input_limit is not None:
            if (
                isinstance(supervisor_input_limit, bool)
                or not isinstance(supervisor_input_limit, int)
                or supervisor_input_limit <= 4
            ):
                raise ValueError("supervisor max_input_bytes must leave room for the 4-byte frame header")
            max_frame_bytes = min(max_frame_bytes, supervisor_input_limit - 4)
        self._supervisor = supervisor
        self._worker_spec = worker_spec
        self._max_frame_bytes = max_frame_bytes
        self._request_lock = threading.RLock()
        self._active_requests: dict[str, WorkerInvocationHandle] = {}

    @staticmethod
    def _validate_request_id(request_id: str) -> None:
        if (
            not isinstance(request_id, str)
            or not request_id.strip()
            or len(request_id) > 128
            or "\x00" in request_id
        ):
            raise WorkerIPCError("worker.request_invalid", "request_id is invalid")

    def reserve(self, request_id: str) -> WorkerInvocationHandle:
        """Reserve a unique worker identity before admission reaches process start."""
        self._validate_request_id(request_id)
        with self._request_lock:
            if request_id in self._active_requests:
                raise WorkerIPCError(
                    "worker.request_already_active",
                    "request_id is already active in this WorkerIPCClient",
                )
            handle = WorkerInvocationHandle(
                request_id=request_id,
                worker_id=f"worker-{uuid4().hex}",
            )
            self._active_requests[request_id] = handle
            return handle

    def release(self, handle: WorkerInvocationHandle) -> bool:
        """Release an unused/completed reservation; stale handles cannot release a newer one."""
        if not isinstance(handle, WorkerInvocationHandle):
            return False
        with self._request_lock:
            if self._active_requests.get(handle.request_id) != handle:
                return False
            self._active_requests.pop(handle.request_id, None)
            return True

    def request(
        self,
        frame: WorkerFrame,
        *,
        handle: WorkerInvocationHandle | None = None,
        on_process_started: Callable[[ProcessIdentity], object] | None = None,
        host_instance_id: str | None = None,
    ) -> WorkerFrame:
        """Send one REQUEST using its pre-reserved identity and return one correlated RESPONSE."""
        if not isinstance(frame, WorkerFrame):
            raise TypeError("frame must be a WorkerFrame")
        if frame.message_type != "REQUEST":
            raise WorkerIPCError("worker.invalid_request_type", "only REQUEST frames can be dispatched")
        self._validate_request_id(frame.request_id)
        if handle is None:
            handle = self.reserve(frame.request_id)
        elif (
            not isinstance(handle, WorkerInvocationHandle)
            or handle.request_id != frame.request_id
        ):
            raise WorkerIPCError("worker.request_handle_invalid", "worker handle does not match request_id")
        with self._request_lock:
            if self._active_requests.get(frame.request_id) != handle:
                raise WorkerIPCError("worker.request_handle_invalid", "worker handle is not the active reservation")
        worker_id = handle.worker_id

        try:
            if on_process_started is not None:
                if not callable(on_process_started):
                    raise WorkerIPCError("worker.identity_handoff_invalid", "process identity callback is invalid")
                if not isinstance(host_instance_id, str) or not host_instance_id.strip() or "\\x00" in host_instance_id:
                    raise WorkerIPCError("worker.identity_handoff_invalid", "host_instance_id is required for identity hand-off")
                if not callable(getattr(self._supervisor, "run_with_identity", None)):
                    raise WorkerIPCError(
                        "worker.identity_handoff_unavailable",
                        "supervisor does not support identity-gated worker startup",
                    )
            elif host_instance_id is not None:
                raise WorkerIPCError("worker.identity_handoff_invalid", "host_instance_id requires an identity callback")

            try:
                encoded = encode_frame(frame, max_frame_bytes=self._max_frame_bytes)
            except WorkerProtocolError as error:
                raise WorkerIPCError("worker.request_invalid", "request frame is invalid") from error

            try:
                spec = replace(
                    self._worker_spec,
                    worker_id=worker_id,
                    stdin_data=encoded,
                )
            except (TypeError, ValueError) as error:
                raise WorkerIPCError("worker.request_invalid", "request could not be assigned to a worker") from error

            try:
                if on_process_started is None:
                    result = self._supervisor.run(spec)
                else:
                    result = self._supervisor.run_with_identity(
                        spec,
                        host_instance_id=host_instance_id,
                        on_process_started=on_process_started,
                    )
            except WorkerTerminationError as error:
                raise WorkerIPCError(
                    "worker.termination_unconfirmed",
                    "supervisor could not confirm worker process-tree termination",
                    termination_confirmed=False,
                ) from error
            except Exception as error:
                raise WorkerIPCError(
                    "worker.identity_handoff_failed" if on_process_started is not None else "worker.supervisor_failed",
                    "worker process identity could not be durably recorded before payload start"
                    if on_process_started is not None else
                    "supervised worker execution failed",
                    termination_confirmed=True,
                ) from error

            if result.timed_out:
                raise WorkerIPCError("worker.timeout", "worker exceeded its host-owned deadline")
            if result.cancelled:
                raise WorkerIPCError("worker.cancelled", "worker was cancelled by the host")
            if result.exit_code != 0:
                raise WorkerIPCError("worker.nonzero_exit", "worker exited unsuccessfully")
            if result.output_truncated:
                raise WorkerIPCError("worker.response_truncated", "worker response exceeded the output limit")

            raw = getattr(result, "stdout_bytes", None)
            if not isinstance(raw, bytes):
                raise WorkerIPCError("worker.raw_output_unavailable", "supervisor did not provide raw stdout bytes")
            if not raw:
                raise WorkerIPCError("worker.response_missing", "worker returned no response frame")

            stream = BytesIO(raw)
            try:
                response = read_frame(stream, max_frame_bytes=self._max_frame_bytes)
            except WorkerProtocolError as error:
                raise WorkerIPCError("worker.response_invalid", "worker returned an invalid response frame") from error
            if response is None:
                raise WorkerIPCError("worker.response_missing", "worker returned no response frame")
            if stream.read(1):
                raise WorkerIPCError("worker.response_trailing_data", "worker returned trailing bytes after its response")
            if response.message_type != "RESPONSE":
                raise WorkerIPCError("worker.response_type_mismatch", "worker did not return a RESPONSE frame")
            if response.request_id != frame.request_id:
                raise WorkerIPCError("worker.response_correlation_mismatch", "worker response request_id did not match")
            return response
        finally:
            # ModuleRuntime also releases in its outer finally so a reservation
            # is removed when resource admission fails before request() starts.
            self.release(handle)

    def cancel(
        self,
        handle: WorkerInvocationHandle,
        *,
        grace_seconds: float = 1.0,
    ) -> bool:
        """Cancel only the process identity captured by this invocation handle."""
        if not isinstance(handle, WorkerInvocationHandle):
            return False
        if (
            isinstance(grace_seconds, bool)
            or not isinstance(grace_seconds, (int, float))
            or not math.isfinite(grace_seconds)
            or grace_seconds < 0
        ):
            return False
        deadline = time.monotonic() + max(0.1, grace_seconds + 1.0)
        while True:
            try:
                if self._supervisor.cancel(handle.worker_id, grace_seconds=grace_seconds):
                    return True
            except Exception:  # noqa: BLE001
                # Cancellation is a boolean control API. The request thread
                # independently reports unconfirmed cleanup and retains leases.
                return False
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)


__all__ = ["WorkerIPCClient", "WorkerIPCError", "WorkerInvocationHandle"]
