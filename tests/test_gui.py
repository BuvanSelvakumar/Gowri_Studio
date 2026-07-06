"""Headless GUI smoke tests (offscreen). Skipped if PySide6 isn't installed."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QMessageBox


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    # Stub modal dialogs so tests never block.
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    QMessageBox.warning = staticmethod(lambda *a, **k: None)
    yield app


def test_mainwindow_builds(qapp):
    from PySide6.QtWidgets import QTabWidget
    from passport_cropper.gui.app import MainWindow
    win = MainWindow()
    tabs = win.findChild(QTabWidget)
    assert tabs is not None and tabs.count() == 2
    assert win.uploads is not None and win.config is not None


def test_config_save_roundtrip(qapp, monkeypatch):
    from passport_cropper.gui.app import MainWindow
    win = MainWindow()
    # Don't touch the real settings.json during tests.
    monkeypatch.setattr(win.state.settings, "save", lambda *a, **k: None)
    win.config.max_roll.setValue(11.0)
    win.config._save_settings()
    assert win.state.settings.tilt.max_roll == 11.0


def test_start_does_not_autosave_but_save_all_writes(qapp, tmp_path):
    from pathlib import Path

    from passport_cropper.detect import LANDMARKER_MODEL
    dsc = sorted(Path("sample").glob("DSC_*.jpeg")) if Path("sample").exists() else []
    if not LANDMARKER_MODEL.exists() or not dsc:
        pytest.skip("models or samples missing")

    from passport_cropper.detect import FaceAnalyzer
    from passport_cropper.gui.app import MainWindow
    from passport_cropper.pipeline import process_image
    from passport_cropper.presets import get_preset

    win = MainWindow()
    win.state.settings.output_dir = str(tmp_path)
    f = dsc[0]
    win.uploads.files = [f]
    win.uploads._populate_pending()
    res = process_image(f, get_preset("india_35x45"), FaceAnalyzer(), win.state.settings)
    win.uploads._on_file_done(res)
    assert not list(tmp_path.glob("*.jpg"))     # nothing auto-saved
    win.uploads._save_all()
    assert list(tmp_path.glob("*.jpg"))         # written only on Save all


def test_editor_apply_matches_output_size(qapp):
    from passport_cropper.crop import CropRect
    from passport_cropper.gui.editor import ManualCropDialog
    from passport_cropper.presets import get_preset

    preset = get_preset("india_35x45")
    img = np.full((1200, 1000, 3), 200, np.uint8)
    dlg = ManualCropDialog(img, CropRect(100, 100, 822 * 0.6, 1050 * 0.6), preset)
    dlg.rot.setValue(50)          # rotate 5 degrees
    dlg._apply()
    assert dlg.result_bgr is not None
    assert dlg.result_bgr.shape[:2] == (preset.output_px[1], preset.output_px[0])
