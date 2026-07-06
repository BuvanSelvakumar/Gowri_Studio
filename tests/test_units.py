"""Fast unit tests (no models): presets, crop math, config, quality, filesize."""

import math

import numpy as np
import pytest
from PIL import Image

from factory import make_face, make_preset

from passport_cropper.config import Settings
from passport_cropper.crop import compute_crop, within_bounds
from passport_cropper.filesize import fit_jpeg_to_size
from passport_cropper.presets import get_preset
from passport_cropper.quality import run_checks


# --- presets -------------------------------------------------------------
def test_default_preset_loads():
    p = get_preset("india_35x45")
    assert p.output_px == (822, 1050)
    assert p.dpi == 600
    assert math.isclose(p.aspect, 822 / 1050)


def test_unknown_preset_raises():
    with pytest.raises(KeyError):
        get_preset("nope")


# --- crop math -----------------------------------------------------------
def test_compute_crop_places_head_fraction():
    preset = make_preset(head_fraction=0.5, top_margin=0.1)
    face = make_face(crown_y=200, chin_y=400, center_x=400)  # head_h = 200
    rect = compute_crop(face, preset)
    assert math.isclose(rect.h, 400.0)                       # 200 / 0.5
    assert math.isclose(rect.w, 400.0 * preset.aspect)
    assert math.isclose(rect.x + rect.w / 2, 400.0)          # centered on eyes
    assert math.isclose(rect.y, 200 - 0.1 * 400)             # top margin above crown


def test_within_bounds():
    preset = make_preset()
    rect = compute_crop(make_face(), preset)
    assert within_bounds(rect, 100000, 100000)
    assert not within_bounds(rect, 10, 10)


# --- config --------------------------------------------------------------
def test_settings_roundtrip(tmp_path):
    s = Settings()
    s.output_format = "PNG"
    s.tilt.max_roll = 12.0
    s.target_kb = 150
    path = tmp_path / "settings.json"
    s.save(path)
    loaded = Settings.load(path)
    assert loaded.output_format == "PNG"
    assert loaded.tilt.max_roll == 12.0
    assert loaded.target_kb == 150


def test_settings_defaults_when_missing(tmp_path):
    s = Settings.load(tmp_path / "absent.json")
    assert s.preset == "india_35x45"
    assert "eyes_closed" in s.checks


# --- quality -------------------------------------------------------------
def _blank(w=800, h=1000):
    return np.full((h, w, 3), 128, np.uint8)


def test_quality_clean_face_has_no_findings():
    preset = make_preset()
    # Big, centered head in a large frame -> a valid full-size crop, no warnings.
    face = make_face(center_x=2000, crown_y=500, chin_y=1100,
                     eye_open=0.3, mouth_open=0.1, roll=0, yaw=0, pitch=0)
    rect = compute_crop(face, preset)
    findings = run_checks(face, rect, _blank(4000, 5000), preset, Settings())
    assert findings == []


def test_quality_flags_closed_eyes_and_pose():
    preset = make_preset()
    face = make_face(eye_open=0.05, yaw=25, mouth_open=0.6)
    rect = compute_crop(face, preset)
    checks = {f.check for f in run_checks(face, rect, _blank(4000, 5000), preset, Settings())}
    assert {"eyes_closed", "not_facing_forward", "mouth_open"} <= checks


def test_quality_check_can_be_disabled():
    preset = make_preset()
    s = Settings()
    s.checks["eyes_closed"]["enabled"] = False
    face = make_face(eye_open=0.02)
    rect = compute_crop(face, preset)
    checks = {f.check for f in run_checks(face, rect, _blank(4000, 5000), preset, s)}
    assert "eyes_closed" not in checks


# --- filesize ------------------------------------------------------------
def test_fit_jpeg_hits_target():
    # Noisy (hard to compress) image with an achievable target exercises the
    # quality search: it must land under target by lowering quality.
    img = Image.effect_noise((822, 1050), 80).convert("RGB")
    full = len(fit_jpeg_to_size(img, dpi=600, target_kb=100000)[0])  # ~max size
    data, q = fit_jpeg_to_size(img, dpi=600, target_kb=200)
    assert len(data) <= 200 * 1024 < full
    assert 5 <= q <= 100
