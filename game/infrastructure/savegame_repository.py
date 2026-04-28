from __future__ import annotations

import json
from pathlib import Path


class SaveGameRepositoryError(Exception):
    """Base error for savegame persistence failures."""


class SaveGameLoadError(SaveGameRepositoryError):
    """Raised when a save file cannot be read or parsed."""


class SaveGameWriteError(SaveGameRepositoryError):
    """Raised when a save file cannot be written."""


class JsonSaveGameRepository:
    """Infrastructure adapter responsible only for JSON file IO."""

    def __init__(self, save_file: Path | None = None) -> None:
        self.save_file = save_file or Path("savegame.json")

    def exists(self) -> bool:
        return self.save_file.exists()

    def load(self) -> dict[str, object]:
        try:
            return json.loads(self.save_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SaveGameLoadError from exc

    def save(self, data: dict[str, object]) -> None:
        try:
            payload = json.dumps(data, ensure_ascii=True, separators=(",", ":"))
            self.save_file.write_text(payload, encoding="utf-8")
        except (OSError, TypeError, ValueError) as exc:
            raise SaveGameWriteError from exc
