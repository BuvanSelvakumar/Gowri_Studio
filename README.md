# Passport Photo Auto-Cropper

Offline desktop app (Windows + Mac) that batch-crops normal photos into
compliant passport photos by detecting and tracking the face. Detection uses
bundled MediaPipe models that run locally on the CPU — no internet, no cloud.

## Features
- **Batch** a whole folder → passport crops at the preset's exact size (India
  35×45 mm / 822×1050 px @ 600 DPI by default).
- **Face tracking**: 478-point landmarks + head-top (crown) via segmentation.
- **Auto-orientation**: fixes sideways/rotated inputs using the body-below-face
  signal (robust against MediaPipe's upside-down false detections).
- **Tilt correction**: auto-levels head roll; flags turned/tipped faces.
- **Quality checks**: margin, resolution, pose, closed eyes, open mouth, uneven
  lighting — each configurable (off / warn / fail).
- **Manual crop editor**: aspect-locked move/resize, rotate, crown/chin guides.
- **Configurable output**: JPEG/PNG/PDF, quality, and optional file-size (KB).
- Same filename → new output folder; flagged originals → `flagged photos/`.

## Setup
```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
Model files live in `models/` (`face_landmarker.task`, `selfie_segmenter.tflite`).

## Run — desktop app
```bash
.venv/bin/python run_app.py
```
Two tabs: **Uploads** (pick files/folder → Start → review/edit results) and
**Configuration** (presets + all settings).

## Run — command line (batch)
```bash
.venv/bin/python -m passport_cropper.cli sample --preset india_35x45 \
    --output output --target-kb 100 --debug
```
`--debug` also writes detection overlays to `output/debug/`.

## Build a standalone app

### macOS
```bash
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller passport_cropper.spec
```
Output: `dist/Gowri Studio.app` — drag it to `/Applications`.

### Windows — easiest (automatic)
Copy the whole project folder (including `models/` and `assets/`) to a Windows PC,
then **double-click `Gowri Studio (Windows).bat`**. On the first run it
automatically installs Python 3.12, sets up the environment, installs everything,
and launches the app. Every run after that just opens the app instantly.
(If Windows shows a blue "Windows protected your PC" box, click **More info → Run anyway**.)

### Windows — make a standalone `.exe` (optional)
To produce a self-contained `.exe` you can copy to other PCs (PyInstaller can't
cross-build, so this runs on Windows):
```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt pyinstaller
.venv\Scripts\pyinstaller passport_cropper.spec
```
Output: `dist\Gowri Studio\Gowri Studio.exe` — double-click, or pin to Start. The
spec auto-uses `assets\AppIcon.ico` on Windows.

> Use Python **3.12/3.11** on Windows — MediaPipe wheels are most reliable there.
> The code is identical and fully cross-platform.

## Tests
```bash
.venv/bin/python -m pytest
```
Unit tests (crop math, config, quality, file-size), integration tests on the
sample photos, and headless GUI smoke tests.

## Project layout
```
passport_cropper/
  presets.py     size presets (presets.json)
  config.py      settings (settings.json): format, quality, tilt, checks, KB
  detect.py      MediaPipe landmarks + crown + pose + eye/mouth metrics
  crop.py        crop geometry
  quality.py     configurable quality checks
  filesize.py    JPEG file-size targeting
  pipeline.py    orient -> straighten -> crop -> check -> render/save
  cli.py         batch command line
  resources.py   source/bundle-aware paths
  gui/           PySide6 app (uploads, configuration, manual editor)
models/          bundled ML models
sample/          sample input + reference photos
tests/           pytest suite
```

## Presets
Edit `presets.json` (or the Configuration page). Each preset:
```json
{ "india_35x45": { "label": "India Passport 35×45mm",
  "width_mm": 35, "height_mm": 45, "dpi": 600,
  "output_px": [822, 1050], "head_fraction": 0.57, "top_margin": 0.07 } }
```
`head_fraction` = chin→crown as a share of the photo height (calibrated from
real samples); `top_margin` = gap above the crown as a share of the crop height.
