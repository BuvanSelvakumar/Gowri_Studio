# Passport Photo Auto-Cropper — Build Plan

> **Status: implemented.** CLI + PySide6 GUI (Uploads/Configuration/manual editor),
> quality checks, tilt & auto-orientation, file-size targeting, and PyInstaller
> packaging are built and covered by a 19-test pytest suite (units + real-sample
> integration + headless GUI). See `README.md`. Remaining: run the platform
> builds (`.exe` on Windows) and finalize calibration on the full sample set.

## What we're building
An **offline cross-platform desktop app (Windows + Mac)** that batch-crops normal
photos into compliant passport photos by detecting and tracking the face. One
codebase, packaged as a `.exe` and a `.app`.

- **Input:** JPEG / PNG (full or half-body shots).
- **Output:** passport crops at the preset's exact size.
- **First preset:** India 35×45 mm, on a configurable preset system so more sizes drop in later.
- **Two screens:** an **Uploads page** (batch) and a **Configuration page** (presets + settings).
- **Background:** kept as-is (crop only — you shoot on the final backdrop).

---

## Locked specifications

| Item | Decision |
|---|---|
| Output size (India) | **822 × 1050 px @ 600 DPI** (≈35×45 mm), aspect 7:9 — matches your samples |
| Head height (chin→crown) | ~0.55–0.6 of photo height — **finalized in calibration** |
| Head position | horizontally centered on the eyes; small margin above crown |
| Input formats | JPEG / PNG (no RAW) |
| Output format | JPEG (default), PNG, or PDF — configurable, set **globally** |
| Output location | **new folder**, **same filename** as source |
| Flagged photos | originals copied to a **`flagged photos/` subfolder** inside the output folder |
| Tilt — roll (fixable) | auto-straighten up to **±15°**, else flag |
| Tilt — yaw/pitch (not fixable) | flag beyond **±10°** |
| File-size targeting | optional — user enters target KB, app compresses/enlarges to match |
| One person per photo | yes — multiple faces are flagged as unexpected |

---

## How it works — the pipeline
Each photo runs through:

```
0. Fix orientation   — EXIF auto-orient + auto-rotate upright (raws come sideways)
1. Detect face       — landmarks: eyes, nose, chin                      [AI model]
2. Straighten roll   — rotate so the eye line is level (≤±15°, else flag)
3. Estimate crown    — head/hair top via segmentation                   [AI model]
4. Compute crop      — preset math (below)
5. Bounds check      — flag if the photo lacks margin around the head
6. Crop + resize     — to 822×1050, write 600 DPI metadata
7. Quality checks    — attach ✓ / ⚠ / ✗ (see below)
8. File-size target  — optional: hit a target KB
9. Save              — same filename → output folder (flagged → flagged photos/)
```

**Detection = AI models; cropping = pure math.** The models are lightweight,
pre-trained, and run offline on CPU — no cloud, no GPU, no training, no internet.

### Orientation (step 0)
Your raw files are stored sideways with the EXIF flag stripped. The tool:
- applies EXIF orientation when present, and
- when it's missing/wrong, tries face detection at 0° / 90° / 180° / 270° and keeps the upright result.

### Crop math (step 4)
Given the preset's aspect ratio `R = w/h` and head-height fraction `F`, measured on the straightened image:

```
chin_y   = bottom of face (landmarks)
crown_y  = top of head (segmentation)
head_h   = chin_y − crown_y
crop_h   = head_h / F                 # head becomes F of the photo
crop_w   = crop_h × R
center_x = midpoint between the eyes  # horizontal centering
top_y    = crown_y − topMargin × crop_h
```
Then crop → resize to 822×1050 → set 600 DPI. Compliance is tuned entirely by `F` and `topMargin`.

---

## Quality checks (step 7)
Each crop is scored; results show in the list with a reason. Each check is configurable (on/off, threshold, warn-vs-fail).

| Check | Type |
|---|---|
| Face too small / too large | Reliable (math) |
| Head not centered | Reliable |
| Residual tilt after straightening | Reliable |
| Looking away (yaw/pitch) | Reliable |
| Too low resolution | Reliable |
| Eyes closed | Advisory (heuristic) |
| Mouth open / not neutral | Advisory |
| Uneven lighting / harsh shadow | Advisory |

Result per photo = **✓ pass**, **⚠ warning** (croppable, review), or **✗ fail** (needs manual fix). Warnings/fails go to the review queue.

## Manual crop editor
For photos auto-crop gets wrong (or you disagree), an interactive editor:
- Full photo with the crop box overlaid, **locked to the preset aspect ratio** (drag to move, resize by corners — can't go out of spec).
- **Rotate slider** for fine tilt, with a level grid.
- **Guide overlays:** crown / eye / chin lines + target head-size band.
- Live preview, zoom/pan; **Reset to auto / Apply / Skip**.
- Reached from any result row's **Edit** button and auto-offered for the review queue.
- **Apply** renders through the same path as auto — identical output quality.

---

## The two pages

**Uploads page** — drag-drop / select files or folder · preset dropdown · output folder · Start + progress + Cancel · results list (✓/⚠/✗ + thumbnail) · **Edit** → manual editor · review queue · Open output folder · Export report.

**Configuration page** — preset manager (add/edit/delete: label, mm, DPI, output_px, head_fraction, top_margin) · global settings (output folder, format, quality, recurse, parallel) · file-size targeting · tilt settings (±15° / ±10°) · quality-check toggles + thresholds · Save.

## Batch processing
- Folder (optionally recursive) or multi-selected files.
- Runs the pipeline per photo; **never stops the batch on one failure** — flags and continues to the end.
- Optional parallel processing across CPU cores.
- **When the whole batch finishes**, show the summary (clean / warnings / flagged). If any photos were flagged, ask what to do:
  - **Export & finish** → save the good crops and copy the flagged originals into the `flagged photos/` subfolder. Done.
  - **Review now** → open the flagged photos one at a time in the **manual crop editor**; fix each, then finish.

---

## Tech stack
- **Python 3.12** (MediaPipe requires ≤3.12; your 3.13 needs a 3.12 env).
- **Detection:** MediaPipe Face Mesh (landmarks) + Selfie Segmentation (crown).
- **Image ops:** OpenCV + Pillow (EXIF auto-orient, crop, resize, DPI, file-size targeting).
- **GUI:** PySide6 (Qt) — two pages +o the manual editor (QGraphicsView).
- **Packaging:** PyInstaller → `.exe` (Windows) and `.app` (Mac). Fully offline.

## Preset system
Editable `presets.json` — new sizes need no code:
```json
{
  "india_35x45": {
    "label": "India Passport 35×45mm",
    "width_mm": 35, "height_mm": 45, "dpi": 600,
    "output_px": [822, 1050],
    "head_fraction": 0.57, "top_margin": 0.07
  }
}
```

---

## Build phases
- **0 — Setup:** Python 3.12 env, dependencies, project skeleton.
- **1 — Detection core:** orientation fix + landmarks + crown + roll/yaw-pitch, with a debug overlay.
- **2 — Crop engine:** crop math + preset loading + output at 822×1050/600 DPI + file-size targeting (CLI first).
- **3 — Calibration:** measure your reference samples → finalize `head_fraction` / `top_margin`.
- **4 — Quality checks:** implement the checks with configurable thresholds.
- **5 — Batch engine:** folder processing, review queue, summary report.
- **6 — GUI:** Uploads + Configuration pages, drag-drop, progress/cancel.
- **7 — Manual editor:** aspect-locked interactive crop wired into the review queue.
- **8 — Packaging:** build `.exe` + `.app`, test on clean machines, one-page guide.

## Deliverables
- **Windows `.exe`** + **Mac `.app`** (same app).
- Editable `presets.json`; per-batch report; short usage guide.

## Not in v1 (later)
- Background replacement · print-sheet tiling (copies on a 4×6) · more country presets (US, UK/Schengen).

---

## Calibration inputs (received)
- 5 reference passport photos (822×1050 @ 600 DPI, blue bg) — to set head-size/margins.
- 5 raw camera shots (24 MP Nikon, 6000×4000, white bg, sideways) — real inputs to test on.
