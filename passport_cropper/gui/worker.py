"""Background batch worker so the UI stays responsive."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..config import Settings
from ..detect import FaceAnalyzer
from ..pipeline import PhotoResult, process_image
from ..presets import Preset
from ..quality import Finding

EXT = {"JPEG": ".jpg", "PNG": ".png", "PDF": ".pdf"}


class BatchWorker(QThread):
    """Processes photos in memory only — nothing is written to disk here.
    Saving happens later when the user clicks Save all."""

    progress = Signal(int, int, str)     # done, total, filename
    file_done = Signal(object)           # PhotoResult (crop held in memory)
    done = Signal(int, int, int)         # ok, warn, flagged

    def __init__(self, files, preset: Preset, settings: Settings):
        super().__init__()
        self.files = [Path(f) for f in files]
        self.preset = preset
        self.settings = settings
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        analyzer = FaceAnalyzer()
        n_ok = n_warn = n_flag = 0

        for i, f in enumerate(self.files):
            if self._cancel:
                break
            try:
                res = process_image(f, self.preset, analyzer, self.settings)
            except Exception as exc:  # never kill the batch on one bad file
                res = PhotoResult(src=str(f), status="flagged",
                                  findings=[Finding("error", "fail", str(exc))])

            if res.status == "ok":
                n_ok += 1
            elif res.status == "warning":
                n_warn += 1
            else:
                n_flag += 1

            self.file_done.emit(res)
            self.progress.emit(i + 1, len(self.files), f.name)

        self.done.emit(n_ok, n_warn, n_flag)
