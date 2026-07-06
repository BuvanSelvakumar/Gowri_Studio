"""Integration tests: run the real models on the bundled sample photos.

Skipped automatically if the model files or sample images aren't present.
"""

from pathlib import Path

import pytest

from passport_cropper.detect import LANDMARKER_MODEL, SEGMENTER_MODEL, FaceAnalyzer
from passport_cropper.pipeline import process_image
from passport_cropper.presets import get_preset

SAMPLES = Path(__file__).resolve().parent.parent / "sample"
# Whatever DSC raws are actually present (the sample set may change over time).
DSC = sorted(p.name for p in SAMPLES.glob("DSC_*.jpeg")) if SAMPLES.exists() else []

models_ok = LANDMARKER_MODEL.exists() and SEGMENTER_MODEL.exists()
pytestmark = pytest.mark.skipif(
    not (models_ok and DSC), reason="models or sample images missing"
)


@pytest.fixture(scope="module")
def analyzer():
    return FaceAnalyzer()


@pytest.fixture(scope="module")
def preset():
    return get_preset("india_35x45")


@pytest.mark.parametrize("name", DSC)
def test_dsc_produces_upright_passport_crop(analyzer, preset, name):
    r = process_image(SAMPLES / name, preset, analyzer)
    assert r.status in ("ok", "warning"), f"{name}: {r.flags}"
    assert r.cropped is not None
    assert r.cropped.shape[:2] == (preset.output_px[1], preset.output_px[0])
    # The chosen orientation must be upright: eyes above nose above chin.
    assert r.face.chin[1] > r.face.nose[1] > r.face.eye_mid[1]
    # And roughly level after straightening.
    assert abs(r.face.roll_deg) < 3.0


def test_reference_photo_flags_insufficient_margin(analyzer, preset):
    # Already-cropped passport photos have no room to re-crop -> must flag.
    r = process_image(SAMPLES / "Aadav R.jpg.jpeg", preset, analyzer)
    assert "insufficient_margin" in r.flags
