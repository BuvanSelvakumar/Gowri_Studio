"""Opening splash that plays the branded welcome video, then reveals the app.

Uses OpenCV to decode frames (no QtMultimedia backend needed, so it bundles
cleanly). Click or press any key to skip.
"""

from __future__ import annotations

import cv2
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QWidget

from .util import bgr_to_pixmap


class SplashScreen(QWidget):
    finished = Signal()

    def __init__(self, video_path, max_w: int = 780):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
        )
        self._cap = cv2.VideoCapture(str(video_path))
        self.ok = self._cap.isOpened()
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30
        vw = self._cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280
        vh = self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720
        self._w = max_w
        self._h = int(max_w * vh / max(vw, 1))
        self.setFixedSize(self._w, self._h)
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self._w, self._h)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next)
        self._interval = max(1, int(1000 / max(fps, 1)))
        self._done = False

    def start(self):
        if not self.ok:
            self._finish()
            return
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.move(scr.center().x() - self._w // 2, scr.center().y() - self._h // 2)
        self.show()
        self.raise_()
        self._timer.start(self._interval)

    def _next(self):
        ok, frame = self._cap.read()
        if not ok:
            self._finish()
            return
        self.label.setPixmap(bgr_to_pixmap(cv2.resize(frame, (self._w, self._h))))

    def _finish(self):
        if self._done:
            return
        self._done = True
        self._timer.stop()
        try:
            self._cap.release()
        except Exception:
            pass
        self.finished.emit()
        self.close()

    def mousePressEvent(self, _e):
        self._finish()

    def keyPressEvent(self, _e):
        self._finish()
