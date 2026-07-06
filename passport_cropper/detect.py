"""Face detection: 478-point landmarks + crown (top of head) via segmentation.

Detection uses MediaPipe's Tasks API (FaceLandmarker + ImageSegmenter). Images
are downscaled for detection speed; all returned coordinates are mapped back to
the full-resolution input frame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# Landmark indices in the 478-point model (with iris refinement).
L_IRIS, R_IRIS = 468, 473
CHIN, FOREHEAD, NOSE = 152, 10, 1
# Eye contour (for eye-aspect-ratio) and mouth (for openness).
LE_OUT, LE_IN, LE_TOP, LE_BOT = 33, 133, 159, 145
RE_IN, RE_OUT, RE_TOP, RE_BOT = 362, 263, 386, 374
MOUTH_TOP, MOUTH_BOT, MOUTH_L, MOUTH_R = 13, 14, 61, 291

# Longest edge used for detection. Full-res crops still come from the original.
DETECT_MAX_DIM = 1280

from .resources import bundled

MODELS_DIR = bundled("models")
LANDMARKER_MODEL = MODELS_DIR / "face_landmarker.task"
SEGMENTER_MODEL = MODELS_DIR / "selfie_segmenter.tflite"


@dataclass
class Face:
    left_eye: tuple[float, float]
    right_eye: tuple[float, float]
    eye_mid: tuple[float, float]
    chin: tuple[float, float]
    crown: tuple[float, float]
    nose: tuple[float, float]
    box: tuple[float, float, float, float]  # x0, y0, x1, y1
    roll_deg: float
    yaw_deg: float
    pitch_deg: float
    body_below: float = 0.0  # fraction of the person silhouette below the nose
    eye_open: float = 1.0    # min eye-aspect-ratio (small => eyes closed)
    mouth_open: float = 0.0  # lip gap / mouth width (large => mouth open)

    @property
    def head_height(self) -> float:
        return self.chin[1] - self.crown[1]


class FaceAnalyzer:
    """Wraps the landmarker + segmenter. Reusable across many images."""

    def __init__(
        self,
        landmarker_path: str | Path = LANDMARKER_MODEL,
        segmenter_path: str | Path = SEGMENTER_MODEL,
        max_faces: int = 5,
    ):
        self._landmarker = vision.FaceLandmarker.create_from_options(
            vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(landmarker_path)),
                num_faces=max_faces,
                output_facial_transformation_matrixes=True,
                running_mode=vision.RunningMode.IMAGE,
            )
        )
        self._segmenter = vision.ImageSegmenter.create_from_options(
            vision.ImageSegmenterOptions(
                base_options=mp_python.BaseOptions(model_asset_path=str(segmenter_path)),
                output_category_mask=True,
                running_mode=vision.RunningMode.IMAGE,
            )
        )

    def detect(self, image_bgr: np.ndarray) -> list[Face]:
        """Return faces (largest first) with coords in full-res input space."""
        h, w = image_bgr.shape[:2]
        scale = min(1.0, DETECT_MAX_DIM / max(h, w))
        small = (
            cv2.resize(image_bgr, (round(w * scale), round(h * scale)))
            if scale < 1.0
            else image_bgr
        )
        sh, sw = small.shape[:2]
        rgb = np.ascontiguousarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self._landmarker.detect(mp_img)
        if not result.face_landmarks:
            return []

        cmask = self._segmenter.segment(mp_img).category_mask.numpy_view()
        if cmask.ndim == 3:
            cmask = cmask[:, :, 0]
        # Person silhouette: the mask label sampled on the first face's nose.
        n0 = result.face_landmarks[0][NOSE]
        person = cmask == cmask[
            int(min(max(n0.y * sh, 0), sh - 1)), int(min(max(n0.x * sw, 0), sw - 1))
        ]
        total_person = max(int(person.sum()), 1)

        inv = 1.0 / scale
        matrices = result.facial_transformation_matrixes or []
        faces: list[Face] = []
        for i, lms in enumerate(result.face_landmarks):
            def pt(idx: int) -> tuple[float, float]:
                p = lms[idx]
                return (p.x * sw, p.y * sh)

            le, re = pt(L_IRIS), pt(R_IRIS)
            chin, fore, nose = pt(CHIN), pt(FOREHEAD), pt(NOSE)
            xs = [lm.x * sw for lm in lms]
            ys = [lm.y * sh for lm in lms]
            box_s = (min(xs), min(ys), max(xs), max(ys))
            crown_s = self._crown(person, box_s, fore)

            nose_row = int(min(max(nose[1], 0), sh - 1))
            body_below = float(person[nose_row:, :].sum()) / total_person
            roll = math.degrees(math.atan2(re[1] - le[1], re[0] - le[0]))
            yaw, pitch = _pose_angles(matrices[i] if i < len(matrices) else None)

            ear_l = _dist(pt(LE_TOP), pt(LE_BOT)) / max(_dist(pt(LE_OUT), pt(LE_IN)), 1e-6)
            ear_r = _dist(pt(RE_TOP), pt(RE_BOT)) / max(_dist(pt(RE_IN), pt(RE_OUT)), 1e-6)
            eye_open = min(ear_l, ear_r)
            mouth_open = _dist(pt(MOUTH_TOP), pt(MOUTH_BOT)) / max(_dist(pt(MOUTH_L), pt(MOUTH_R)), 1e-6)

            def up(p: tuple[float, float]) -> tuple[float, float]:
                return (p[0] * inv, p[1] * inv)

            faces.append(
                Face(
                    left_eye=up(le),
                    right_eye=up(re),
                    eye_mid=up(((le[0] + re[0]) / 2, (le[1] + re[1]) / 2)),
                    chin=up(chin),
                    crown=up(crown_s),
                    nose=up(nose),
                    box=(box_s[0] * inv, box_s[1] * inv, box_s[2] * inv, box_s[3] * inv),
                    roll_deg=roll,
                    yaw_deg=yaw,
                    pitch_deg=pitch,
                    body_below=body_below,
                    eye_open=eye_open,
                    mouth_open=mouth_open,
                )
            )

        faces.sort(key=lambda f: f.box[3] - f.box[1], reverse=True)
        return faces

    @staticmethod
    def _crown(person: np.ndarray, box, fore) -> tuple[float, float]:
        """Top of the head (incl. hair): highest person pixel over the face span."""
        x0 = int(max(0, box[0]))
        x1 = int(min(person.shape[1], box[2]))
        if x1 <= x0:
            return (fore[0], fore[1])
        rows = np.where(person[:, x0:x1].any(axis=1))[0]
        crown_y = float(rows.min()) if len(rows) else fore[1]
        return ((box[0] + box[2]) / 2, crown_y)


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _pose_angles(matrix) -> tuple[float, float]:
    """Approximate (yaw, pitch) in degrees from the facial transform matrix."""
    if matrix is None:
        return (0.0, 0.0)
    r = np.array(matrix, dtype=float)[:3, :3]
    sy = math.sqrt(r[0, 0] ** 2 + r[1, 0] ** 2)
    pitch = math.degrees(math.atan2(r[2, 1], r[2, 2]))
    yaw = math.degrees(math.atan2(-r[2, 0], sy))
    return (yaw, pitch)
