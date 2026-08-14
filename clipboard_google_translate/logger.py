"""CSV logging of source/translated text pairs."""

from __future__ import annotations

import csv
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional


class TranslationLogger:
    def __init__(self, log_dir: Optional[Path] = None) -> None:
        self.log_dir = log_dir or (Path(__file__).resolve().parent / "LOG")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_log.csv"
        self.log_path = self.log_dir / self.log_name

        self._last_saved: Optional[str] = None

    def save(self, source_text: str, translated_text: str) -> bool:
        """Append a row. Returns False (no-op) if source_text was already
        the last thing saved, so repeated clicks don't duplicate rows."""
        if not source_text or source_text == self._last_saved:
            return False

        is_new_file = not self.log_path.exists()
        with open(self.log_path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if is_new_file:
                writer.writerow(["source", "translated"])
            writer.writerow([source_text, translated_text])

        self._last_saved = source_text
        return True

    def open_folder(self) -> None:
        """Open the log directory in Windows Explorer."""
        subprocess.Popen(["explorer", str(self.log_dir)])
