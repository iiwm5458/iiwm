from __future__ import annotations

from pathlib import Path
from typing import Iterable


class RunLogger:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lines: list[str] = []

    def info(self, message: str) -> None:
        self.lines.append(f"[INFO] {message}")

    def warning(self, message: str) -> None:
        self.lines.append(f"[WARN] {message}")

    def error(self, message: str) -> None:
        self.lines.append(f"[ERROR] {message}")

    def extend(self, messages: Iterable[str]) -> None:
        for message in messages:
            self.info(message)

    def save(self, name: str = "arena_ocr.log") -> Path:
        path = self.output_dir / name
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        return path

