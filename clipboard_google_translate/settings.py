"""Persisted app settings (window size, language, toggles).

Saved on demand (via the Settings window's Save button), not on every
change -- so a user can experiment with toggles without them sticking
until they explicitly want that.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional

DEFAULT_PATH = Path(__file__).resolve().parent / "settings.json"


@dataclass
class AppSettings:
    dest_lang: str = "vi"
    ocr_enabled: bool = True
    overwrite_clipboard: bool = False
    font_size: int = 11
    window_width: int = 580
    window_height: int = 285

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppSettings":
        path = path or DEFAULT_PATH
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            return cls()

        known = {f.name for f in fields(cls)}
        return cls(**{**asdict(cls()), **{k: v for k, v in data.items() if k in known}})

    def save(self, path: Optional[Path] = None) -> None:
        path = path or DEFAULT_PATH
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
