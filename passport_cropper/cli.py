"""Command-line batch runner.

Example:
    python -m passport_cropper.cli sample --preset india_35x45 --output output --debug
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

from .config import Settings
from .detect import FaceAnalyzer
from .pipeline import PhotoResult, process_image, save_output
from .presets import get_preset

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
EXT_FOR_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "PDF": ".pdf"}


def collect_images(inputs: list[str], recurse: bool) -> list[Path]:
    files: list[Path] = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            it = p.rglob("*") if recurse else p.glob("*")
            files += [f for f in it if f.suffix.lower() in IMAGE_EXTS]
        elif p.suffix.lower() in IMAGE_EXTS:
            files.append(p)
    return sorted(set(files))


def draw_overlay(result: PhotoResult) -> np.ndarray | None:
    if result.image is None or result.face is None:
        return None
    vis = result.image.copy()
    f = result.face
    for p, col in [(f.left_eye, (0, 255, 0)), (f.right_eye, (0, 255, 0)),
                   (f.chin, (0, 0, 255)), (f.crown, (255, 0, 255)), (f.nose, (0, 255, 255))]:
        cv2.circle(vis, (int(p[0]), int(p[1])), 8, col, -1)
    cv2.line(vis, (int(f.left_eye[0]), int(f.left_eye[1])),
             (int(f.right_eye[0]), int(f.right_eye[1])), (0, 255, 0), 3)
    if result.crop is not None:
        x0, y0, x1, y1 = result.crop.box
        cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 165, 255), 4)
    scale = min(1.0, 900 / max(vis.shape[:2]))
    return cv2.resize(vis, (int(vis.shape[1] * scale), int(vis.shape[0] * scale)))


def build_settings(args) -> Settings:
    s = Settings.load()
    if args.output:
        s.output_dir = args.output
    if args.preset:
        s.preset = args.preset
    if args.format:
        s.output_format = args.format
    if args.quality:
        s.jpeg_quality = args.quality
    if args.target_kb:
        s.target_kb = args.target_kb
    s.recurse = args.recurse
    return s


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Batch passport-photo auto-cropper")
    ap.add_argument("inputs", nargs="+", help="image files and/or folders")
    ap.add_argument("--preset", default="india_35x45")
    ap.add_argument("--output", default="output")
    ap.add_argument("--format", default="JPEG", choices=["JPEG", "PNG", "PDF"])
    ap.add_argument("--quality", type=int, default=95)
    ap.add_argument("--target-kb", type=int, default=None, help="target output size in KB")
    ap.add_argument("--recurse", action="store_true")
    ap.add_argument("--debug", action="store_true", help="also save detection overlays")
    args = ap.parse_args(argv)

    settings = build_settings(args)
    preset = get_preset(settings.preset)
    files = collect_images(args.inputs, settings.recurse)
    if not files:
        print("No images found.", file=sys.stderr)
        return 1

    out_dir = Path(settings.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    flagged_dir = out_dir / "flagged photos"
    debug_dir = out_dir / "debug"
    ext = EXT_FOR_FORMAT[settings.output_format]

    analyzer = FaceAnalyzer()
    print(f"Preset: {preset.label}  ({preset.output_px[0]}x{preset.output_px[1]} @ {preset.dpi} DPI)")
    print(f"Processing {len(files)} image(s)...\n")

    n_ok = n_warn = n_flag = 0
    for f in files:
        result = process_image(f, preset, analyzer, settings, keep_image=args.debug)

        if args.debug:
            vis = draw_overlay(result)
            if vis is not None:
                debug_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(debug_dir / (f.stem + "_debug.png")), vis)

        if result.status in ("ok", "warning") and result.cropped is not None:
            out_path = out_dir / (f.stem + ext)
            save_output(result.cropped, out_path, preset, settings)
            result.output_path = str(out_path)
            if result.status == "ok":
                n_ok += 1
                tag = "OK  "
            else:
                n_warn += 1
                tag = "WARN"
        else:
            n_flag += 1
            flagged_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, flagged_dir / f.name)
            tag = "FLAG"

        note = f"  [{', '.join(result.flags)}]" if result.flags else ""
        print(f"  {tag}  {f.name}{note}")

    print(f"\nDone. {n_ok} clean, {n_warn} with warnings, {n_flag} flagged.")
    print(f"Output: {out_dir.resolve()}")
    if n_flag:
        print(f"Flagged originals: {flagged_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
