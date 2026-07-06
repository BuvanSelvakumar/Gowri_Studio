"""Crop geometry: turn a detected face + preset into a crop rectangle."""

from __future__ import annotations

from dataclasses import dataclass

from .detect import Face
from .presets import Preset


@dataclass
class CropRect:
    x: float
    y: float
    w: float
    h: float

    @property
    def box(self) -> tuple[int, int, int, int]:
        return (round(self.x), round(self.y), round(self.x + self.w), round(self.y + self.h))


def compute_crop(face: Face, preset: Preset) -> CropRect:
    """Place the head so chin->crown is `head_fraction` of the crop height,
    centered horizontally on the eyes, with `top_margin` above the crown."""
    head_h = face.head_height
    crop_h = head_h / preset.head_fraction
    crop_w = crop_h * preset.aspect
    center_x = face.eye_mid[0]
    top_y = face.crown[1] - preset.top_margin * crop_h
    return CropRect(x=center_x - crop_w / 2, y=top_y, w=crop_w, h=crop_h)


def within_bounds(rect: CropRect, image_w: int, image_h: int, tol: float = 1.5) -> bool:
    """True if the crop fits inside the image (enough margin around the head)."""
    return (
        rect.x >= -tol
        and rect.y >= -tol
        and rect.x + rect.w <= image_w + tol
        and rect.y + rect.h <= image_h + tol
    )
