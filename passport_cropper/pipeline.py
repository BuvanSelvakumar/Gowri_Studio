"""End-to-end per-photo pipeline: load -> orient -> straighten -> crop -> check -> save."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from .config import Settings
from .crop import CropRect, compute_crop, within_bounds
from .detect import Face, FaceAnalyzer
from .filesize import save_jpeg
from .presets import Preset
from .quality import Finding, run_checks


@dataclass
class PhotoResult:
    src: str
    status: str                              # "ok" | "warning" | "flagged"
    findings: list[Finding] = field(default_factory=list)
    output_path: str | None = None
    face: Face | None = None
    crop: CropRect | None = None
    cropped: np.ndarray | None = None        # final passport-size BGR crop
    image: np.ndarray | None = None          # straightened full-res BGR (for editor/debug)

    @property
    def flags(self) -> list[str]:
        return [f.check for f in self.findings]


def load_bgr(path: str | Path) -> np.ndarray:
    """Load an image applying EXIF orientation; return a full-res BGR array."""
    pil = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def rotate_bound(image: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate CCW by angle_deg, expanding the canvas so nothing is clipped."""
    h, w = image.shape[:2]
    cx, cy = w / 2, h / 2
    m = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw = int(h * sin + w * cos)
    nh = int(h * cos + w * sin)
    m[0, 2] += nw / 2 - cx
    m[1, 2] += nh / 2 - cy
    return cv2.warpAffine(image, m, (nw, nh), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def _is_upright(face: Face) -> bool:
    """A correctly-oriented face reads top-to-bottom: eyes, then nose, then chin.
    MediaPipe also detects inverted faces, so we must check this explicitly."""
    return face.chin[1] > face.nose[1] > face.eye_mid[1]


def _auto_orient(image: np.ndarray, analyzer: FaceAnalyzer) -> tuple[np.ndarray, list[Face]]:
    """Try 0/90/180/270 and keep the correct one. The reliable signal is the
    body: in a real portrait most of the person's silhouette sits *below* the
    face. MediaPipe fits a plausible upright face even to an inverted image, so
    we rank by (upright, most body-below-face, fewest rotations)."""
    candidates = []
    for k in range(4):
        rot = image if k == 0 else np.ascontiguousarray(np.rot90(image, k))
        faces = analyzer.detect(rot)
        if faces:
            candidates.append((k, rot, faces, _is_upright(faces[0]), faces[0].body_below))
    if not candidates:
        return image, []
    candidates.sort(key=lambda c: (not c[3], -c[4], c[0]))
    _, rot, faces, _, _ = candidates[0]
    return rot, faces


def _status(findings: list[Finding]) -> str:
    if any(f.level == "fail" for f in findings):
        return "flagged"
    if any(f.level == "warn" for f in findings):
        return "warning"
    return "ok"


def process_image(
    path: str | Path,
    preset: Preset,
    analyzer: FaceAnalyzer,
    settings: Settings | None = None,
    keep_image: bool = False,
) -> PhotoResult:
    settings = settings or Settings()
    src = str(path)
    image = load_bgr(path)

    image, faces = _auto_orient(image, analyzer)
    if not faces:
        return PhotoResult(src=src, status="flagged",
                           findings=[Finding("no_face", "fail", "No face detected.")])

    findings: list[Finding] = []
    if len(faces) > 1:
        findings.append(Finding("multiple_faces", "warn",
                                f"{len(faces)} faces found; using the largest."))
    face = faces[0]

    # Straighten roll (level the eyes), then re-detect on the upright image.
    if settings.tilt.auto_straighten and abs(face.roll_deg) > 0.5:
        image = rotate_bound(image, face.roll_deg)
        refined = analyzer.detect(image)
        if refined:
            face = refined[0]

    rect = compute_crop(face, preset)
    findings += run_checks(face, rect, image, preset, settings)

    # A crop image is produced whenever the rectangle actually fits the frame,
    # so the GUI review queue / manual editor has something to start from.
    cropped = _render_crop(image, rect, preset) if within_bounds(rect, *image.shape[1::-1]) else None

    return PhotoResult(
        src=src,
        status=_status(findings),
        findings=findings,
        face=face,
        crop=rect,
        cropped=cropped,
        image=image if keep_image else None,
    )


def _render_crop(image: np.ndarray, rect: CropRect, preset: Preset) -> np.ndarray:
    """Crop (clamped, edge-padded if slightly over) and resize to output pixels."""
    x0, y0, x1, y1 = rect.box
    h, w = image.shape[:2]
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    crop = image[cy0:cy1, cx0:cx1]
    pad_l, pad_t, pad_r, pad_b = cx0 - x0, cy0 - y0, x1 - cx1, y1 - cy1
    if any(p > 0 for p in (pad_l, pad_t, pad_r, pad_b)):
        crop = cv2.copyMakeBorder(crop, pad_t, pad_b, pad_l, pad_r, cv2.BORDER_REPLICATE)
    return cv2.resize(crop, preset.output_px, interpolation=cv2.INTER_AREA)


def save_output(image_bgr: np.ndarray, path: str | Path, preset: Preset,
                settings: Settings | None = None) -> None:
    settings = settings or Settings()
    pil = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    fmt = settings.output_format.upper()
    if fmt in ("JPEG", "JPG"):
        save_jpeg(pil, path, preset.dpi, settings.jpeg_quality,
                  settings.target_kb, settings.target_kb_min)
    elif fmt == "PDF":
        pil.save(path, format="PDF", dpi=(preset.dpi, preset.dpi))
    else:
        pil.save(path, format="PNG", dpi=(preset.dpi, preset.dpi))
