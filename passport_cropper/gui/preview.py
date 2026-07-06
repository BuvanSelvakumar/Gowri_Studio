"""Full-size image preview dialog for a result crop (or the original)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from .util import bgr_to_pixmap


def open_in_os(path: str):
    p = str(Path(path).resolve())
    if sys.platform == "darwin":
        subprocess.run(["open", p])
    elif sys.platform.startswith("win"):
        os.startfile(p)  # opens files in the default app and folders in Explorer
    else:
        subprocess.run(["xdg-open", p])


class ImagePreviewDialog(QDialog):
    def __init__(self, bgr: np.ndarray, title: str, subtitle: str = "",
                 file_path: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._file = file_path

        head = QLabel(title)
        head.setObjectName("title")
        sub = QLabel(subtitle)
        sub.setObjectName("subtitle")

        img = QLabel()
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = bgr_to_pixmap(bgr)
        h = bgr.shape[0]
        if h > 720:
            pix = pix.scaledToHeight(720, Qt.TransformationMode.SmoothTransformation)
        img.setPixmap(pix)

        open_btn = QPushButton("Open file")
        open_btn.setObjectName("primary")
        open_btn.setEnabled(bool(file_path))
        open_btn.clicked.connect(lambda: file_path and open_in_os(file_path))
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(open_btn)
        row.addWidget(close)

        lay = QVBoxLayout(self)
        lay.addWidget(head)
        lay.addWidget(sub)
        lay.addWidget(img, 1)
        lay.addLayout(row)
