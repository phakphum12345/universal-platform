import io
import struct

import pytest

from universal_platform.runtime.worker_protocol import (
    DEFAULT_MAX_FRAME_BYTES,
    WorkerFrame,
    WorkerProtocolError,
    encode_frame,
    read_frame,
    write_frame,
)


def test_round_trip_versioned_request_frame():
    frame = WorkerFrame("REQUEST", "req-123", {"module_id": "org.example.calc", "inputs": {"x": 2}})
    encoded = encode_frame(frame)
    assert struct.unpack("!I", encoded[:4])[0] == len(encoded) - 4
    assert read_frame(io.BytesIO(encoded)) == frame


def test_clean_eof_is_distinct_from_truncated_frame():
    assert read_frame(io.BytesIO(b"")) is None
    with pytest.raises(WorkerProtocolError, match="truncated"):
        read_frame(io.BytesIO(b"\x00\x00"))


def test_rejects_oversized_and_zero_length_frames():
    with pytest.raises(WorkerProtocolError, match="size limit"):
        encode_frame(WorkerFrame("REQUEST", "r1", {"data": "x" * 100}), max_frame_bytes=32)
    with pytest.raises(WorkerProtocolError, match="zero"):
        read_frame(io.BytesIO(struct.pack("!I", 0)))


def test_rejects_incoming_oversized_length_before_body_read():
    with pytest.raises(WorkerProtocolError, match="size limit"):
        read_frame(io.BytesIO(struct.pack("!I", DEFAULT_MAX_FRAME_BYTES + 1)))


@pytest.mark.parametrize("body", [
    b'{"protocol_version":"1.0","message_type":"REQUEST","request_id":"r","payload":{},"extra":1}',
    b'{"protocol_version":"9.0","message_type":"REQUEST","request_id":"r","payload":{}}',
    b'{"protocol_version":"1.0","message_type":"UNKNOWN","request_id":"r","payload":{}}',
    b'{"protocol_version":"1.0","message_type":"REQUEST","request_id":"r","payload":{},"payload":{}}',
    b'{"protocol_version":"1.0","message_type":"REQUEST","request_id":"r","payload":{"n":NaN}}',
    b'not-json',
])
def test_rejects_malformed_or_unsupported_envelopes(body):
    with pytest.raises(WorkerProtocolError):
        read_frame(io.BytesIO(struct.pack("!I", len(body)) + body))


def test_rejects_non_object_payload_and_empty_request_id():
    with pytest.raises(WorkerProtocolError, match="payload"):
        WorkerFrame("REQUEST", "r1", [])
    with pytest.raises(WorkerProtocolError, match="request_id"):
        WorkerFrame("REQUEST", " ", {})


def test_write_frame_flushes_and_round_trips():
    class FlushBuffer(io.BytesIO):
        flushed = False
        def flush(self):
            self.flushed = True
    stream = FlushBuffer()
    frame = WorkerFrame("CANCEL", "req-9", {"reason": "user"})
    write_frame(stream, frame)
    assert stream.flushed
    stream.seek(0)
    assert read_frame(stream) == frame


def test_rejects_non_finite_values_on_encode():
    with pytest.raises(WorkerProtocolError, match="finite"):
        encode_frame(WorkerFrame("RESPONSE", "r1", {"value": float("inf")}))
