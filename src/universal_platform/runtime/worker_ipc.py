"""One-shot request/response client for explicitly supervised trusted workers.

The host supplies the allow-listed WorkerSpec template. The client sends one
bounded REQUEST frame on stdin, requires exactly one correlated RESPONSE frame
on stdout, and delegates cancellation to the process supervisor. This is not
a persistent channel or a security sandbox.
"""
from __future__ import annotations

from dataclasses import replace
from io import BytesIO

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
        self._supervisor = supervisor
        self._worker_spec = worker_spec
        self._max_frame_bytes = max_frame_bytes

    def request(self, frame: WorkerFrame) -> WorkerFrame:
        """Send one REQUEST and return its exactly correlated RESPONSE."""
        if not isinstance(frame, WorkerFrame):
            raise TypeError("frame must be a WorkerFrame")
        if frame.message_type != "REQUEST":
            raise WorkerIPCError("worker.invalid_request_type", "only REQUEST frames can be dispatched")

        try:
            encoded = encode_frame(frame, max_frame_bytes=self._max_frame_bytes)
        except WorkerProtocolError as error:
            raise WorkerIPCError("worker.request_invalid", "request frame is invalid") from error

        spec = replace(
            self._worker_spec,
            worker_id=frame.request_id,
            stdin_data=encoded,
        )
        try:
            result = self._supervisor.run(spec)
        except WorkerTerminationError as error:
            raise WorkerIPCError(
                "worker.termination_unconfirmed",
                "supervisor could not confirm worker process-tree termination",
                termination_confirmed=False,
            ) from error
        except Exception as error:
            raise WorkerIPCError(
                "worker.supervisor_failed",
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

    def cancel(self, request_id: str, *, grace_seconds: float = 1.0) -> bool:
        """Cancel the supervised process tree for an in-flight request."""
        if (
            not isinstance(request_id, str)
            or not request_id.strip()
            or len(request_id) > 128
            or "\x00" in request_id
        ):
            raise ValueError("request_id must be a non-empty string of at most 128 characters")
        return bool(self._supervisor.cancel(request_id, grace_seconds=grace_seconds))


__all__ = ["WorkerIPCClient", "WorkerIPCError"]
