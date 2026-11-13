"""Versioned, bounded framing primitives for trusted worker IPC.

Transport only: this module does not launch workers, authorize modules, or
provide a security sandbox. The host remains the authority for permissions.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import struct
from typing import BinaryIO, Literal

PROTOCOL_VERSION = "1.0"
DEFAULT_MAX_FRAME_BYTES = 1_048_576
_HEADER = struct.Struct("!I")
_MESSAGE_TYPES = frozenset({"REQUEST", "RESPONSE", "CANCEL"})


class WorkerProtocolError(ValueError):
    """Malformed, unsupported, or oversized worker protocol data."""


@dataclass(frozen=True, slots=True)
class WorkerFrame:
    message_type: Literal["REQUEST", "RESPONSE", "CANCEL"]
    request_id: str
    payload: dict[str, object]
    protocol_version: str = PROTOCOL_VERSION

    def __post_init__(self) -> None:
        if self.protocol_version != PROTOCOL_VERSION:
            raise WorkerProtocolError("unsupported protocol version")
        if self.message_type not in _MESSAGE_TYPES:
            raise WorkerProtocolError("unsupported message type")
        if not isinstance(self.request_id, str) or not self.request_id.strip() or len(self.request_id) > 128:
            raise WorkerProtocolError("request_id must be a non-empty string of at most 128 characters")
        if not isinstance(self.payload, dict):
            raise WorkerProtocolError("payload must be a JSON object")


def _reject_constant(value: str):
    raise WorkerProtocolError(f"non-finite JSON number is not allowed: {value}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise WorkerProtocolError("duplicate JSON object key")
        result[key] = value
    return result


def encode_frame(frame: WorkerFrame, *, max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES) -> bytes:
    if isinstance(max_frame_bytes, bool) or not isinstance(max_frame_bytes, int) or max_frame_bytes < 1:
        raise ValueError("max_frame_bytes must be a positive integer")
    document = {
        "protocol_version": frame.protocol_version,
        "message_type": frame.message_type,
        "request_id": frame.request_id,
        "payload": frame.payload,
    }
    try:
        body = json.dumps(
            document, ensure_ascii=False, allow_nan=False,
            separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise WorkerProtocolError("frame payload is not finite UTF-8 JSON") from error
    if not body or len(body) > max_frame_bytes:
        raise WorkerProtocolError("frame exceeds configured size limit")
    return _HEADER.pack(len(body)) + body


def _read_exact(stream: BinaryIO, size: int, *, allow_clean_eof: bool = False) -> bytes | None:
    chunks = bytearray()
    while len(chunks) < size:
        part = stream.read(size - len(chunks))
        if not part:
            if allow_clean_eof and not chunks:
                return None
            raise WorkerProtocolError("truncated IPC frame")
        chunks.extend(part)
    return bytes(chunks)


def read_frame(stream: BinaryIO, *, max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES) -> WorkerFrame | None:
    if isinstance(max_frame_bytes, bool) or not isinstance(max_frame_bytes, int) or max_frame_bytes < 1:
        raise ValueError("max_frame_bytes must be a positive integer")
    header = _read_exact(stream, _HEADER.size, allow_clean_eof=True)
    if header is None:
        return None
    (length,) = _HEADER.unpack(header)
    if length == 0 or length > max_frame_bytes:
        raise WorkerProtocolError("frame length is zero or exceeds configured size limit")
    body = _read_exact(stream, length)
    try:
        document = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except WorkerProtocolError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WorkerProtocolError("frame body is not valid UTF-8 JSON") from error
    if not isinstance(document, dict) or set(document) != {
        "protocol_version", "message_type", "request_id", "payload"
    }:
        raise WorkerProtocolError("frame must contain exactly the required envelope fields")
    try:
        return WorkerFrame(
            protocol_version=document["protocol_version"],
            message_type=document["message_type"],
            request_id=document["request_id"],
            payload=document["payload"],
        )
    except (TypeError, WorkerProtocolError) as error:
        if isinstance(error, WorkerProtocolError):
            raise
        raise WorkerProtocolError("frame envelope fields have invalid types") from error


def write_frame(stream: BinaryIO, frame: WorkerFrame, *, max_frame_bytes: int = DEFAULT_MAX_FRAME_BYTES) -> None:
    data = memoryview(encode_frame(frame, max_frame_bytes=max_frame_bytes))
    while data:
        written = stream.write(data)
        if written is None or written <= 0:
            raise OSError("IPC stream made no forward progress")
        data = data[written:]
    flush = getattr(stream, "flush", None)
    if callable(flush):
        flush()
