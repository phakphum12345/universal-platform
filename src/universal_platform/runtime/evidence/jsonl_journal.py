"""Reusable bounded JSONL append journal with cross-process locking and hash chaining."""
from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from uuid import uuid4


class JsonlHashChainJournal:
    """Durable append-only JSONL journal for versioned event dictionaries.

    Every chained record includes a monotonically increasing sequence, the
    previous record hash, and its own SHA-256 hash. Optional legacy-prefix
    support exists only for stores that already have a documented migration
    contract; new journals should keep it disabled.
    """

    _ZERO_HASH = "0" * 64
    _CHAIN_FIELDS = frozenset({"sequence", "previous_hash", "record_hash"})

    def __init__(
        self,
        root: str | Path,
        *,
        filename: str = "events.jsonl",
        max_record_bytes: int = 65_536,
        max_store_bytes: int = 16_777_216,
        allow_legacy_prefix: bool = False,
    ) -> None:
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("journal root must be a directory")
        if not filename or Path(filename).name != filename or filename in {".", ".."}:
            raise ValueError("journal filename must be a simple file name")
        if filename.casefold().endswith(".lock"):
            raise ValueError("journal filenames ending in .lock are reserved for lock files")
        if (
            isinstance(max_record_bytes, bool)
            or not isinstance(max_record_bytes, int)
            or max_record_bytes < 256
        ):
            raise ValueError("max_record_bytes must be an integer of at least 256")
        if (
            isinstance(max_store_bytes, bool)
            or not isinstance(max_store_bytes, int)
            or max_store_bytes < max_record_bytes
        ):
            raise ValueError("max_store_bytes must be an integer at least max_record_bytes")
        if not isinstance(allow_legacy_prefix, bool):
            raise ValueError("allow_legacy_prefix must be a boolean")  # noqa: TRY004
        self.path = self.root / filename
        self.lock_path = self.root / f"{filename}.lock"
        self.max_record_bytes = max_record_bytes
        self.max_store_bytes = max_store_bytes
        self.allow_legacy_prefix = allow_legacy_prefix
        self._lock = Lock()

    def append(self, record: Mapping[str, object]) -> dict[str, object]:
        """Append one JSON object and fsync it before returning the chained envelope."""
        appended = self.append_transaction(lambda _records: (record,))
        if not appended:
            raise RuntimeError("single-record append unexpectedly produced no event")
        return appended[0]

    def append_transaction(self, build_records):
        """Atomically inspect verified records and append a derived event batch.

        The callback executes while both the in-process and cross-process locks
        are held. It receives an immutable tuple of copied, verified records
        and must return an iterable of event mappings. Returning an empty
        iterable performs a read-only transaction. Callback or validation
        failures append nothing.
        """
        if not callable(build_records):
            raise TypeError("build_records must be callable")

        with self._lock, self._cross_process_lock():
            descriptor = self._open_journal_file()
            try:
                current = self._read_all(descriptor)
                sequence, previous_hash, _legacy_count, records = self._verify_bytes(
                    current, include_records=True
                )
                proposed = tuple(build_records(tuple(dict(item) for item in records)))
                payloads: list[bytes] = []
                envelopes: list[dict[str, object]] = []
                for record in proposed:
                    if not isinstance(record, Mapping):
                        raise TypeError("journal transaction events must be mappings")
                    envelope = dict(record)
                    if self._CHAIN_FIELDS.intersection(envelope):
                        raise ValueError("journal record must not supply reserved chain fields")
                    if any(not isinstance(key, str) or not key for key in envelope):
                        raise ValueError("journal record keys must be non-empty strings")
                    envelope["sequence"] = sequence + 1
                    envelope["previous_hash"] = previous_hash
                    canonical = self._canonical_json(envelope)
                    envelope["record_hash"] = hashlib.sha256(canonical).hexdigest()
                    payload = self._canonical_json(envelope) + b"\n"
                    if len(payload) > self.max_record_bytes:
                        raise ValueError("journal record exceeds the configured byte limit")
                    payloads.append(payload)
                    envelopes.append(dict(envelope))
                    sequence += 1
                    previous_hash = envelope["record_hash"]
                combined = b"".join(payloads)
                if len(current) + len(combined) > self.max_store_bytes:
                    raise ValueError("journal store reached its configured total byte limit")
                if combined:
                    os.lseek(descriptor, 0, os.SEEK_END)
                    view = memoryview(combined)
                    while view:
                        written = os.write(descriptor, view)
                        if written <= 0:
                            raise OSError("incomplete journal transaction append")
                        view = view[written:]
                    os.fsync(descriptor)
                return tuple(envelopes)
            finally:
                os.close(descriptor)

    def read_all(self) -> tuple[dict[str, object], ...]:
        """Read and verify the complete journal before returning immutable records."""
        with self._lock, self._cross_process_lock():
            descriptor = self._open_journal_file()
            try:
                data = self._read_all(descriptor)
                _sequence, _head_hash, _legacy_count, records = self._verify_bytes(data, include_records=True)
                return tuple(records)
            finally:
                os.close(descriptor)

    def verify(self) -> tuple[int, int, str]:
        """Return (record_count, legacy_prefix_count, chain_head_hash)."""
        with self._lock, self._cross_process_lock():
            descriptor = self._open_journal_file()
            try:
                data = self._read_all(descriptor)
                sequence, head_hash, legacy_count = self._verify_bytes(data)
                return sequence, legacy_count, head_hash
            finally:
                os.close(descriptor)

    @staticmethod
    def _canonical_json(value: Mapping[str, object]) -> bytes:
        try:
            return json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("journal record must contain finite JSON-compatible values") from exc

    def _open_journal_file(self) -> int:
        self._ensure_file_exists(self.path)
        if self.path.is_symlink():
            raise ValueError("journal file must not be a symbolic link")
        # Use binary mode on Windows so CRLF translation cannot make
        # os.read return fewer bytes than fstat reports. Writers seek to EOF
        # explicitly while holding the shared journal lock.
        flags = os.O_RDWR
        flags |= getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_BINARY", 0)
        descriptor = os.open(self.path, flags)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ValueError("journal target must be a regular file")
        return descriptor

    def _ensure_file_exists(self, path: Path, *, initial_bytes: bytes = b"") -> None:
        """Create a file with durable directory-entry semantics on each OS."""
        if path.is_symlink():
            raise ValueError("journal target must not be a symbolic link")
        if path.exists():
            return
        if os.name == "nt":
            temporary = self.root / f".{path.name}.{uuid4().hex}.tmp"
            flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, "O_BINARY", 0)
            descriptor = os.open(temporary, flags, 0o600)
            try:
                if initial_bytes:
                    view = memoryview(initial_bytes)
                    while view:
                        written = os.write(descriptor, view)
                        if written <= 0:
                            raise OSError("incomplete temporary journal file write")
                        view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            try:
                self._move_file_write_through(temporary, path)
            except FileExistsError:
                if path.is_symlink():
                    raise ValueError("journal target must not be a symbolic link")
            finally:
                if temporary.exists():
                    temporary.unlink()
            return

        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_BINARY", 0)
        try:
            descriptor = os.open(path, flags, 0o600)
        except FileExistsError:
            if path.is_symlink():
                raise ValueError("journal target must not be a symbolic link")
            return
        try:
            if initial_bytes:
                view = memoryview(initial_bytes)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError("incomplete initial journal file write")
                    view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        directory_descriptor = os.open(self.root, directory_flags)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)

    @staticmethod
    def _move_file_write_through(source: Path, destination: Path) -> None:
        """Atomically create a Windows directory entry with write-through."""
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        move_file = kernel32.MoveFileExW
        move_file.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
        move_file.restype = wintypes.BOOL
        # MOVEFILE_WRITE_THROUGH (0x8); do not replace an existing journal.
        if not move_file(str(source), str(destination), 0x8):
            error = ctypes.get_last_error()
            if error in (80, 183):  # ERROR_FILE_EXISTS / ERROR_ALREADY_EXISTS
                raise FileExistsError(error, os.strerror(error), str(destination))
            raise OSError(error, os.strerror(error), str(destination))

    def _read_all(self, descriptor: int) -> bytes:
        size = os.fstat(descriptor).st_size
        if size > self.max_store_bytes:
            raise ValueError("journal exceeds the configured total byte limit")
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 65_536))
            if not chunk:
                raise OSError("could not read complete journal")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _verify_bytes(
        self,
        data: bytes,
        *,
        include_records: bool = False,
    ) -> tuple[int, str, int] | tuple[int, str, int, list[dict[str, object]]]:
        if data and not data.endswith(b"\n"):
            raise ValueError("journal ends with an incomplete record")
        sequence = 0
        previous_hash = self._ZERO_HASH
        legacy_count = 0
        chain_started = False
        records: list[dict[str, object]] = []
        for raw in data.splitlines():
            if len(raw) + 1 > self.max_record_bytes:
                raise ValueError("journal record exceeds the configured byte limit")
            try:
                envelope = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("journal contains invalid JSON") from exc
            if not isinstance(envelope, dict):
                raise ValueError("journal record must be a JSON object")  # noqa: TRY004
            present = self._CHAIN_FIELDS.intersection(envelope)
            if not present:
                if not self.allow_legacy_prefix or chain_started:
                    raise ValueError("legacy journal record is not allowed here")
                legacy_count += 1
                sequence += 1
                previous_hash = hashlib.sha256(raw).hexdigest()
                records.append(dict(envelope))
                continue
            if present != self._CHAIN_FIELDS:
                raise ValueError("journal chain metadata is incomplete")
            chain_started = True
            claimed_hash = envelope.pop("record_hash")
            claimed_sequence = envelope.get("sequence")
            claimed_previous = envelope.get("previous_hash")
            if isinstance(claimed_sequence, bool) or not isinstance(claimed_sequence, int):
                raise ValueError("journal sequence must be an integer")  # noqa: TRY004
            if claimed_sequence != sequence + 1 or claimed_previous != previous_hash:
                raise ValueError("journal sequence or previous hash mismatch")
            actual_hash = hashlib.sha256(self._canonical_json(envelope)).hexdigest()
            if not isinstance(claimed_hash, str) or claimed_hash != actual_hash:
                raise ValueError("journal hash-chain verification failed")
            envelope["record_hash"] = claimed_hash
            sequence = claimed_sequence
            previous_hash = actual_hash
            records.append(dict(envelope))
        if include_records:
            return sequence, previous_hash, legacy_count, records
        return sequence, previous_hash, legacy_count

    @contextmanager
    def _cross_process_lock(self) -> Iterator[None]:
        self._ensure_file_exists(self.lock_path, initial_bytes=b"0")
        if self.lock_path.is_symlink():
            raise ValueError("journal lock file must not be a symbolic link")
        flags = os.O_RDWR
        flags |= getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_BINARY", 0)
        descriptor = os.open(self.lock_path, flags)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("journal lock target must be a regular file")
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"0")
                os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(descriptor, fcntl.LOCK_EX)
            try:
                yield
            finally:
                os.lseek(descriptor, 0, os.SEEK_SET)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


__all__ = ["JsonlHashChainJournal"]
