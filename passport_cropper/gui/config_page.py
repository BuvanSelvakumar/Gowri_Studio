"""Configuration page: edit the preset and all global/tilt/quality settings."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

from ..presets import load_presets, load_raw, save_raw

CHECK_LABELS = {
    "insufficient_margin": "Not enough margin",
    "low_resolution": "Low resolution",
    "not_facing_forward": "Not facing forward",
    "excessive_tilt": "Excessive tilt",
    "eyes_closed": "Eyes closed",
    "mouth_open": "Mouth open / not neutral",
    "uneven_lighting": "Uneven lighting",
}


class ConfigPage(QWidget):
    def __init__(self, state):
        super().__init__()
        self.state = state
        self._build()
        self._load_preset_fields()

    def _build(self):
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        lay = QVBoxLayout(inner)
        outer.addWidget(scroll)

        # --- preset editor ------------------------------------------------
        pg = QGroupBox("Preset")
        pf = QFormLayout(pg)
        self.preset_combo = QComboBox()
        for key, p in self.state.presets.items():
            self.preset_combo.addItem(p.label, key)
        self.preset_combo.currentIndexChanged.connect(self._load_preset_fields)
        self.f_label = QLineEdit()
        self.f_w_mm = _dspin(1, 200)
        self.f_h_mm = _dspin(1, 200)
        self.f_dpi = _ispin(72, 1200)
        self.f_out_w = _ispin(50, 5000)
        self.f_out_h = _ispin(50, 5000)
        self.f_head = _dspin(0.2, 0.95, step=0.01, decimals=3)
        self.f_margin = _dspin(0.0, 0.4, step=0.01, decimals=3)
        pf.addRow("Preset", self.preset_combo)
        pf.addRow("Label", self.f_label)
        pf.addRow("Width (mm)", self.f_w_mm)
        pf.addRow("Height (mm)", self.f_h_mm)
        pf.addRow("DPI", self.f_dpi)
        pf.addRow("Output width (px)", self.f_out_w)
        pf.addRow("Output height (px)", self.f_out_h)
        pf.addRow("Head fraction", self.f_head)
        pf.addRow("Top margin", self.f_margin)
        save_preset = QPushButton("Save preset")
        save_preset.clicked.connect(self._save_preset)
        pf.addRow(save_preset)
        lay.addWidget(pg)

        # --- global settings ---------------------------------------------
        gg = QGroupBox("Output")
        gf = QFormLayout(gg)
        s = self.state.settings
        self.fmt = QComboBox(); self.fmt.addItems(["JPEG", "PNG", "PDF"])
        self.fmt.setCurrentText(s.output_format)
        self.quality = _ispin(10, 100); self.quality.setValue(s.jpeg_quality)
        self.recurse = QCheckBox("Recurse into subfolders"); self.recurse.setChecked(s.recurse)
        self.parallel = QCheckBox("Use parallel processing"); self.parallel.setChecked(s.parallel)
        self.target_kb = _ispin(0, 100000); self.target_kb.setValue(s.target_kb or 0)
        self.target_kb.setSpecialValueText("off")
        gf.addRow("Format", self.fmt)
        gf.addRow("JPEG quality", self.quality)
        gf.addRow("Target size (KB)", self.target_kb)
        gf.addRow(self.recurse)
        gf.addRow(self.parallel)
        lay.addWidget(gg)

        # --- tilt ---------------------------------------------------------
        tg = QGroupBox("Tilt")
        tf = QFormLayout(tg)
        self.auto_straighten = QCheckBox("Auto-straighten roll")
        self.auto_straighten.setChecked(s.tilt.auto_straighten)
        self.max_roll = _dspin(0, 45); self.max_roll.setValue(s.tilt.max_roll)
        self.max_yaw = _dspin(0, 45); self.max_yaw.setValue(s.tilt.max_yaw)
        self.max_pitch = _dspin(0, 45); self.max_pitch.setValue(s.tilt.max_pitch)
        tf.addRow(self.auto_straighten)
        tf.addRow("Max correctable roll (deg)", self.max_roll)
        tf.addRow("Max yaw before flag (deg)", self.max_yaw)
        tf.addRow("Max pitch before flag (deg)", self.max_pitch)
        lay.addWidget(tg)

        # --- quality checks ----------------------------------------------
        qg = QGroupBox("Quality checks")
        qf = QFormLayout(qg)
        self.check_widgets = {}
        for name, label in CHECK_LABELS.items():
            cfg = s.check(name)
            enabled = QCheckBox("on"); enabled.setChecked(cfg.get("enabled", True))
            level = QComboBox(); level.addItems(["warn", "fail"])
            level.setCurrentText(cfg.get("level", "warn"))
            row = QHBoxLayout(); w = QWidget(); w.setLayout(row)
            row.addWidget(enabled); row.addWidget(QLabel("level:")); row.addWidget(level)
            row.addStretch(1)
            qf.addRow(label, w)
            self.check_widgets[name] = (enabled, level)
        lay.addWidget(qg)

        save_all = QPushButton("Save settings")
        save_all.clicked.connect(self._save_settings)
        lay.addWidget(save_all)
        lay.addStretch(1)

    # --- preset -----------------------------------------------------------
    def _load_preset_fields(self):
        key = self.preset_combo.currentData()
        p = self.state.presets[key]
        self.f_label.setText(p.label)
        self.f_label.setCursorPosition(0)   # show the start, not the end
        self.f_w_mm.setValue(p.width_mm)
        self.f_h_mm.setValue(p.height_mm)
        self.f_dpi.setValue(p.dpi)
        self.f_out_w.setValue(p.output_px[0])
        self.f_out_h.setValue(p.output_px[1])
        self.f_head.setValue(p.head_fraction)
        self.f_margin.setValue(p.top_margin)

    def _save_preset(self):
        key = self.preset_combo.currentData()
        raw = load_raw()
        raw[key] = {
            "label": self.f_label.text(),
            "width_mm": self.f_w_mm.value(),
            "height_mm": self.f_h_mm.value(),
            "dpi": self.f_dpi.value(),
            "output_px": [self.f_out_w.value(), self.f_out_h.value()],
            "head_fraction": round(self.f_head.value(), 3),
            "top_margin": round(self.f_margin.value(), 3),
        }
        save_raw(raw)
        self.state.presets = load_presets()
        QMessageBox.information(self, "Saved", f"Preset '{key}' saved.")

    # --- settings ---------------------------------------------------------
    def _save_settings(self):
        s = self.state.settings
        s.output_format = self.fmt.currentText()
        s.jpeg_quality = self.quality.value()
        s.recurse = self.recurse.isChecked()
        s.parallel = self.parallel.isChecked()
        s.target_kb = self.target_kb.value() or None
        s.tilt.auto_straighten = self.auto_straighten.isChecked()
        s.tilt.max_roll = self.max_roll.value()
        s.tilt.max_yaw = self.max_yaw.value()
        s.tilt.max_pitch = self.max_pitch.value()
        for name, (enabled, level) in self.check_widgets.items():
            s.checks.setdefault(name, {})
            s.checks[name]["enabled"] = enabled.isChecked()
            s.checks[name]["level"] = level.currentText()
        s.save()
        QMessageBox.information(self, "Saved", "Settings saved.")


def _ispin(lo, hi):
    sp = QSpinBox(); sp.setRange(lo, hi); return sp


def _dspin(lo, hi, step=0.5, decimals=1):
    sp = QDoubleSpinBox(); sp.setRange(lo, hi); sp.setSingleStep(step)
    sp.setDecimals(decimals); return sp
