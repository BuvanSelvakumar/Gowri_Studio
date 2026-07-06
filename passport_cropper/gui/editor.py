"""Manual crop editor: aspect-locked crop box with move/resize, a rotate slider,
and crown/chin guide lines. Produces a crop identical in format to the auto path.
"""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (
    QDialog, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QPushButton,
    QSlider, QVBoxLayout,
)

from ..crop import CropRect
from ..presets import Preset
from .util import bgr_to_pixmap

MIN_W = 40.0
HANDLE = 14.0  # scene px hit radius for corner grabbing


def _rotate_same_size(image: np.ndarray, angle: float) -> np.ndarray:
    h, w = image.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(image, m, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


class CropView(QGraphicsView):
    def __init__(self, preset: Preset):
        super().__init__()
        self.preset = preset
        self.aspect = preset.aspect
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints())
        self.setMouseTracking(True)
        self.rect = QRectF()
        self._img_w = self._img_h = 0
        self._mode: str | None = None
        self._fixed = QPointF()
        self._sign = (1, 1)
        self._grab_off = QPointF()
        self._pix_item = None

    def set_image(self, bgr: np.ndarray):
        self._scene.clear()
        pix = bgr_to_pixmap(bgr)
        self._pix_item = self._scene.addPixmap(pix)
        self._img_h, self._img_w = bgr.shape[:2]
        self._scene.setSceneRect(0, 0, self._img_w, self._img_h)
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.viewport().update()

    def set_rect(self, rect: CropRect):
        self.rect = QRectF(rect.x, rect.y, rect.w, rect.h)
        self._clamp()
        self.viewport().update()

    # --- geometry helpers -------------------------------------------------
    def _corners(self):
        r = self.rect
        return [r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()]

    def _clamp(self):
        r = self.rect
        w = min(r.width(), self._img_w)
        h = w / self.aspect
        if h > self._img_h:
            h = self._img_h
            w = h * self.aspect
        x = min(max(r.x(), 0), self._img_w - w)
        y = min(max(r.y(), 0), self._img_h - h)
        self.rect = QRectF(x, y, w, h)

    # --- mouse ------------------------------------------------------------
    def mousePressEvent(self, e):
        p = self.mapToScene(e.position().toPoint())
        thresh = HANDLE / max(self.transform().m11(), 1e-6)
        for i, c in enumerate(self._corners()):
            if (abs(p.x() - c.x()) < thresh) and (abs(p.y() - c.y()) < thresh):
                self._mode = "resize"
                self._fixed = self._corners()[(i + 2) % 4]
                self._sign = (1 if c.x() >= self._fixed.x() else -1,
                              1 if c.y() >= self._fixed.y() else -1)
                return
        if self.rect.contains(p):
            self._mode = "move"
            self._grab_off = p - self.rect.topLeft()

    def mouseMoveEvent(self, e):
        if not self._mode:
            return
        p = self.mapToScene(e.position().toPoint())
        if self._mode == "move":
            self.rect.moveTopLeft(p - self._grab_off)
            self._clamp()
        elif self._mode == "resize":
            w = max(MIN_W, abs(p.x() - self._fixed.x()))
            h = w / self.aspect
            x = self._fixed.x() if self._sign[0] > 0 else self._fixed.x() - w
            y = self._fixed.y() if self._sign[1] > 0 else self._fixed.y() - h
            self.rect = QRectF(x, y, w, h)
            self._clamp()
        self.viewport().update()

    def mouseReleaseEvent(self, e):
        self._mode = None

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._pix_item is not None:
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    # --- overlay ----------------------------------------------------------
    def drawForeground(self, painter, _rect):
        if self.rect.isEmpty():
            return
        painter.setPen(QPen(QColor(255, 165, 0), 0, Qt.PenStyle.SolidLine))
        painter.drawRect(self.rect)
        # crown & chin target guides + vertical centre
        r = self.rect
        crown_y = r.top() + self.preset.top_margin * r.height()
        chin_y = crown_y + self.preset.head_fraction * r.height()
        painter.setPen(QPen(QColor(0, 220, 0), 0, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(r.left(), crown_y), QPointF(r.right(), crown_y))
        painter.drawLine(QPointF(r.left(), chin_y), QPointF(r.right(), chin_y))
        painter.setPen(QPen(QColor(0, 180, 255), 0, Qt.PenStyle.DashLine))
        cx = r.center().x()
        painter.drawLine(QPointF(cx, r.top()), QPointF(cx, r.bottom()))
        # corner handles
        painter.setPen(QPen(QColor(255, 165, 0), 0))
        painter.setBrush(QColor(255, 165, 0))
        hs = HANDLE / max(self.transform().m11(), 1e-6) / 2
        for c in self._corners():
            painter.drawRect(QRectF(c.x() - hs, c.y() - hs, 2 * hs, 2 * hs))


class ManualCropDialog(QDialog):
    def __init__(self, image_bgr: np.ndarray, rect: CropRect, preset: Preset, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual crop")
        self.resize(720, 820)
        self._base = image_bgr
        self._initial = rect
        self.preset = preset
        self.result_bgr: np.ndarray | None = None

        self.view = CropView(preset)
        self.view.set_image(self._base)
        self.view.set_rect(rect)

        self.rot = QSlider(Qt.Orientation.Horizontal)
        self.rot.setRange(-150, 150)   # tenths of a degree
        self.rot.setValue(0)
        self.rot.valueChanged.connect(self._on_rotate)
        rot_row = QHBoxLayout()
        rot_row.addWidget(QLabel("Rotate"))
        rot_row.addWidget(self.rot)
        self.rot_lbl = QLabel("0.0°")
        rot_row.addWidget(self.rot_lbl)

        reset = QPushButton("Reset to auto")
        reset.clicked.connect(self._reset)
        apply = QPushButton("Apply")
        apply.setDefault(True)
        apply.clicked.connect(self._apply)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btns = QHBoxLayout()
        btns.addWidget(reset)
        btns.addStretch(1)
        btns.addWidget(cancel)
        btns.addWidget(apply)

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Drag to move · drag a corner to resize (locked to size) · "
                             "align crown and chin to the green guides"))
        lay.addWidget(self.view, 1)
        lay.addLayout(rot_row)
        lay.addLayout(btns)

    def _on_rotate(self, val: int):
        angle = val / 10.0
        self.rot_lbl.setText(f"{angle:.1f}°")
        self.view.set_image(_rotate_same_size(self._base, angle))

    def _reset(self):
        self.rot.setValue(0)
        self.view.set_image(self._base)
        self.view.set_rect(self._initial)

    def _current_image(self) -> np.ndarray:
        return _rotate_same_size(self._base, self.rot.value() / 10.0)

    def _apply(self):
        img = self._current_image()
        r = self.view.rect
        x0, y0 = int(round(r.x())), int(round(r.y()))
        x1, y1 = int(round(r.x() + r.width())), int(round(r.y() + r.height()))
        h, w = img.shape[:2]
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        crop = img[y0:y1, x0:x1]
        if crop.size == 0:
            self.reject()
            return
        self.result_bgr = cv2.resize(crop, self.preset.output_px, interpolation=cv2.INTER_AREA)
        self.accept()
