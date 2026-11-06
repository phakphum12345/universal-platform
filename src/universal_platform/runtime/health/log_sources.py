"""Permission-bounded read-only log file source."""
from __future__ import annotations
from pathlib import Path
from .log_analyzer import LogEvent, analyze_logs

class FileLogSource:
    """Read UTF-8 logs only from a configured root directory."""
    def __init__(self, root: str | Path, *, max_bytes: int = 1_048_576, source_id: str = "runtime-file-log") -> None:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("log root must be a directory")
        if not source_id.strip():
            raise ValueError("source_id must be non-empty")
        self.max_bytes = max_bytes
        self.source_id = source_id

    def read_text(self, relative_path: str) -> str:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("relative_path must be non-empty")
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("log path must remain relative to the configured root")
        target = (self.root / candidate).resolve(strict=True)
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("log path escapes the configured root") from exc
        if not target.is_file():
            raise ValueError("log source must be a regular file")
        if target.stat().st_size > self.max_bytes:
            raise ValueError("log file exceeds the configured byte limit")
        content = target.read_bytes()
        if len(content) > self.max_bytes:
            raise ValueError("log file exceeds the configured byte limit")
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("log file must be valid UTF-8") from exc

    def read_events(self, relative_path: str) -> tuple[LogEvent, ...]:
        return analyze_logs(self.read_text(relative_path), source=self.source_id)
