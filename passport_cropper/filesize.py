"""Optional output file-size targeting.

For JPEG we binary-search the quality that lands just under the target KB
(keeping the print pixel size fixed). PNG/PDF are lossless/vector, so targeting
only applies to JPEG; others are saved as-is.
"""

from __future__ import annotations

import io

from PIL import Image


def _encode_jpeg(pil: Image.Image, quality: int, dpi: int) -> bytes:
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=quality,
             subsampling=0 if quality >= 90 else 2, dpi=(dpi, dpi))
    return buf.getvalue()


def fit_jpeg_to_size(pil: Image.Image, dpi: int, target_kb: int,
                     min_kb: int | None = None) -> tuple[bytes, int]:
    """Return (jpeg_bytes, quality) for the highest quality whose size <=
    target_kb. Falls back to quality 5 if even that exceeds the target."""
    target = target_kb * 1024
    lo, hi = 5, 100
    best: bytes | None = None
    best_q = 5
    while lo <= hi:
        mid = (lo + hi) // 2
        data = _encode_jpeg(pil, mid, dpi)
        if len(data) <= target:
            best, best_q = data, mid
            lo = mid + 1
        else:
            hi = mid - 1
    if best is None:
        best, best_q = _encode_jpeg(pil, 5, dpi), 5
    return best, best_q


def save_jpeg(pil: Image.Image, path, dpi: int, quality: int = 95,
              target_kb: int | None = None, min_kb: int | None = None) -> None:
    if target_kb:
        data, _ = fit_jpeg_to_size(pil, dpi, target_kb, min_kb)
        with open(path, "wb") as f:
            f.write(data)
    else:
        pil.save(path, format="JPEG", quality=quality,
                 subsampling=0 if quality >= 90 else 2, dpi=(dpi, dpi))
