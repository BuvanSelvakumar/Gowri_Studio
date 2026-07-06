"""Quality checks. Each returns a Finding only when it triggers; the level
(warn/fail) comes from settings so the photographer can tune what blocks a crop.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .config import Settings
from .crop import CropRect, within_bounds
from .detect import Face
from .presets import Preset


@dataclass
class Finding:
    check: str
    level: str      # "warn" | "fail"
    message: str


def run_checks(
    face: Face,
    rect: CropRect,
    image: np.ndarray,
    preset: Preset,
    settings: Settings,
) -> list[Finding]:
    findings: list[Finding] = []
    h, w = image.shape[:2]

    def enabled(name: str) -> dict | None:
        cfg = settings.check(name)
        return cfg if cfg.get("enabled") else None

    if (cfg := enabled("insufficient_margin")) and not within_bounds(rect, w, h):
        findings.append(Finding("insufficient_margin", cfg.get("level", "fail"),
                                "Not enough room around the head to crop."))

    if cfg := enabled("low_resolution"):
        if rect.w < preset.output_px[0] * cfg.get("min_scale", 1.0):
            findings.append(Finding("low_resolution", cfg.get("level", "warn"),
                                    "Source is low-resolution; output will be upscaled."))

    if cfg := enabled("not_facing_forward"):
        if abs(face.yaw_deg) > settings.tilt.max_yaw or abs(face.pitch_deg) > settings.tilt.max_pitch:
            findings.append(Finding("not_facing_forward", cfg.get("level", "warn"),
                                    f"Face turned/tipped (yaw {face.yaw_deg:.0f}, pitch {face.pitch_deg:.0f})."))

    if cfg := enabled("excessive_tilt"):
        if abs(face.roll_deg) > settings.tilt.max_roll:
            findings.append(Finding("excessive_tilt", cfg.get("level", "warn"),
                                    f"Head tilted {face.roll_deg:.0f}deg beyond the correctable limit."))

    if cfg := enabled("eyes_closed"):
        if face.eye_open < cfg.get("ear_threshold", 0.15):
            findings.append(Finding("eyes_closed", cfg.get("level", "warn"),
                                    "Eyes may be closed."))

    if cfg := enabled("mouth_open"):
        if face.mouth_open > cfg.get("open_threshold", 0.35):
            findings.append(Finding("mouth_open", cfg.get("level", "warn"),
                                    "Mouth appears open / not neutral."))

    if cfg := enabled("uneven_lighting"):
        ratio = _lighting_imbalance(face, image)
        if ratio > cfg.get("ratio_threshold", 0.35):
            findings.append(Finding("uneven_lighting", cfg.get("level", "warn"),
                                    "Uneven lighting / harsh shadow across the face."))

    return findings


def _lighting_imbalance(face: Face, image: np.ndarray) -> float:
    """|mean_left - mean_right| / mean over the face box. 0 = even."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = (int(max(0, face.box[0])), int(max(0, face.box[1])),
                      int(min(w, face.box[2])), int(min(h, face.box[3])))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return 0.0
    gray = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype(np.float32)
    mid = gray.shape[1] // 2
    left, right = gray[:, :mid].mean(), gray[:, mid:].mean()
    denom = (left + right) / 2 or 1.0
    return abs(left - right) / denom
