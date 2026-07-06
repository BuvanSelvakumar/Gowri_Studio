"""Small helpers to bridge OpenCV/NumPy images and Qt."""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap


def bgr_to_qimage(bgr: np.ndarray) -> QImage:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgb = np.ascontiguousarray(rgb)
    h, w, _ = rgb.shape
    return QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()


def bgr_to_pixmap(bgr: np.ndarray) -> QPixmap:
    return QPixmap.fromImage(bgr_to_qimage(bgr))


def thumbnail(bgr: np.ndarray, max_side: int = 96) -> np.ndarray:
    h, w = bgr.shape[:2]
    s = min(1.0, max_side / max(h, w))
    return cv2.resize(bgr, (max(1, int(w * s)), max(1, int(h * s))))
