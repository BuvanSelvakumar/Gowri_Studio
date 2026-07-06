"""Uploads page: pick/drag photos, batch-process, review, preview, edit."""

from __future__ import annotations

import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFrame, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QProgressBar,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..detect import FaceAnalyzer
from ..pipeline import load_bgr, process_image, save_output
from ..presets import get_preset
from .editor import ManualCropDialog
from .preview import ImagePreviewDialog, open_in_os
from .util import bgr_to_pixmap, thumbnail
from .worker import EXT, BatchWorker

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
THUMB = 80


class UploadsPage(QWidget):
    def __init__(self, state):
        super().__init__()
        self.setObjectName("page")
        self.setAcceptDrops(True)
        self.state = state
        self.files: list[Path] = []
        self.results: list = []           # aligned with table rows (None = pending)
        self.row_by_src: dict[str, int] = {}
        self._last_roots: list = []       # last picked files/folders (for re-scan)
        self._analyzer_cache: FaceAnalyzer | None = None
        self.worker: BatchWorker | None = None
        self._build()

    # --- ui ---------------------------------------------------------------
    def _build(self):
        title = QLabel("Uploads")
        title.setObjectName("title")
        subtitle = QLabel("Drop your photos or a folder below to batch-crop them.")
        subtitle.setObjectName("subtitle")

        self.dropzone = QFrame()
        self.dropzone.setObjectName("dropzone")
        self.dropzone.setMinimumHeight(120)
        dz = QVBoxLayout(self.dropzone)
        hint = QLabel("Drag photos or a folder here")
        hint.setObjectName("drophint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orlbl = QLabel("or")
        orlbl.setObjectName("dropsub")
        orlbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pick_files = QPushButton("Select files…")
        pick_files.clicked.connect(self._pick_files)
        pick_folder = QPushButton("Select folder…")
        pick_folder.clicked.connect(self._pick_folder)
        picks = QHBoxLayout()
        picks.addStretch(1)
        picks.addWidget(pick_files)
        picks.addWidget(pick_folder)
        picks.addStretch(1)
        self.recurse_cb = QCheckBox("Include photos in subfolders")
        self.recurse_cb.setChecked(self.state.settings.recurse)
        self.recurse_cb.toggled.connect(self._toggle_recurse)
        rc = QHBoxLayout()
        rc.addStretch(1)
        rc.addWidget(self.recurse_cb)
        rc.addStretch(1)

        dz.addStretch(1)
        dz.addWidget(hint)
        dz.addWidget(orlbl)
        dz.addLayout(picks)
        dz.addSpacing(6)
        dz.addLayout(rc)
        dz.addStretch(1)

        self.preset_combo = QComboBox()
        for key, p in self.state.presets.items():
            self.preset_combo.addItem(p.label, key)
        idx = self.preset_combo.findData(self.state.settings.preset)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.out_lbl = QLabel(self._out_text())
        self.out_lbl.setObjectName("subtitle")
        change_out = QPushButton("Change…")
        change_out.clicked.connect(self._change_out)
        opts = QHBoxLayout()
        opts.addWidget(QLabel("Preset:"))
        opts.addWidget(self.preset_combo)
        opts.addStretch(1)
        opts.addWidget(self.out_lbl)
        opts.addWidget(change_out)

        self.start_btn = QPushButton("Start")
        self.start_btn.setObjectName("primary")
        self.start_btn.setDefault(True)
        self.start_btn.clicked.connect(self._start)
        self.save_btn = QPushButton("Save all")
        self.save_btn.setObjectName("primary")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_all)
        self.save_sel_btn = QPushButton("Save selected")
        self.save_sel_btn.setEnabled(False)
        self.save_sel_btn.clicked.connect(self._save_selected)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setEnabled(False)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        run_row = QHBoxLayout()
        run_row.addWidget(self.start_btn)
        run_row.addWidget(self.save_btn)
        run_row.addWidget(self.save_sel_btn)
        run_row.addWidget(self.cancel_btn)
        run_row.addWidget(self.progress, 1)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["✓", "", "File", "Status", "Issues", "Actions"])
        self.table.setIconSize(QSize(THUMB, THUMB + 24))
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(THUMB + 30)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setShowGrid(False)
        self.table.cellDoubleClicked.connect(self._preview_row)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # checkbox
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # thumbnail
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # file
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)           # issues
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # actions

        self.status_lbl = QLabel("No files selected.")
        self.status_lbl.setObjectName("subtitle")
        open_out = QPushButton("Open output folder")
        open_out.clicked.connect(lambda: open_in_os(self._ensure_out()))
        bottom = QHBoxLayout()
        bottom.addWidget(self.status_lbl, 1)
        bottom.addWidget(open_out)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)
        lay.addWidget(title)
        lay.addWidget(subtitle)
        lay.addWidget(self.dropzone)
        lay.addLayout(opts)
        lay.addLayout(run_row)
        lay.addWidget(self.table, 1)
        lay.addLayout(bottom)

        # Press Enter (when the Uploads page has focus) to start cropping.
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            sc.activated.connect(self._start_if_ready)

    def _out_text(self) -> str:
        return f"Output:  {Path(self.state.settings.output_dir).resolve()}"

    def _ensure_out(self) -> str:
        out = Path(self.state.settings.output_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)
        return str(out)

    # --- drag & drop ------------------------------------------------------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._hover(True)

    def dragLeaveEvent(self, _e):
        self._hover(False)

    def dropEvent(self, e):
        self._hover(False)
        self._set_files_from_paths([u.toLocalFile() for u in e.mimeData().urls()])

    def _hover(self, on: bool):
        self.dropzone.setProperty("hovering", "true" if on else "false")
        self.dropzone.style().unpolish(self.dropzone)
        self.dropzone.style().polish(self.dropzone)

    def _set_files_from_paths(self, paths):
        self._last_roots = list(paths)
        files: list[Path] = []
        recurse = self.state.settings.recurse
        for p in paths:
            pp = Path(p)
            if pp.is_dir():
                it = pp.rglob("*") if recurse else pp.glob("*")
                files += [f for f in it if f.suffix.lower() in IMAGE_EXTS]
            elif pp.suffix.lower() in IMAGE_EXTS:
                files.append(pp)
        if files:
            self.files = sorted(set(files))
            self._on_files_selected()

    # --- input selection --------------------------------------------------
    def _pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select photos", "", "Images (*.jpg *.jpeg *.png)")
        if paths:
            self._set_files_from_paths(paths)

    def _pick_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select folder")
        if d:
            self._set_files_from_paths([d])

    def _change_out(self):
        d = QFileDialog.getExistingDirectory(self, "Select output folder")
        if d:
            self.state.settings.output_dir = d
            self.state.settings.save()
            self.out_lbl.setText(self._out_text())

    def _toggle_recurse(self, on: bool):
        self.state.settings.recurse = on
        self.state.settings.save()
        # Re-scan the current selection so subfolders are added/removed right away.
        if self._last_roots:
            self._set_files_from_paths(self._last_roots)

    def _on_files_selected(self):
        """Show the picked photos immediately as pending rows with thumbnails."""
        self._populate_pending()
        self.status_lbl.setText(
            f"{len(self.files)} photo(s) loaded — press Start (or Enter) to crop.")
        self.start_btn.setFocus()

    def _populate_pending(self):
        self.table.setRowCount(0)
        self.results = [None] * len(self.files)
        self.row_by_src = {str(f): i for i, f in enumerate(self.files)}
        for i, f in enumerate(self.files):
            self.table.insertRow(i)
            self.table.setItem(i, 0, _check_item())
            icon = QTableWidgetItem()
            pix = _fast_thumb(f, THUMB + 24)
            if pix is not None:
                icon.setIcon(QIcon(pix))
            self.table.setItem(i, 1, icon)
            self.table.setItem(i, 2, QTableWidgetItem(f.name))
            st = QTableWidgetItem("PENDING")
            st.setForeground(QColor(120, 120, 130))
            self.table.setItem(i, 3, st)
            self.table.setItem(i, 4, QTableWidgetItem(""))
            self.table.setCellWidget(i, 5, self._actions_widget(i))
            QApplication.processEvents()  # keep UI responsive while loading thumbs

    # --- run --------------------------------------------------------------
    def _start_if_ready(self):
        if self.files and self.start_btn.isEnabled():
            self._start()

    def _start(self):
        if not self.files:
            QMessageBox.information(self, "No files", "Select or drop photos first.")
            return
        if self.worker and self.worker.isRunning():
            return
        self.state.settings.preset = self.preset_combo.currentData()
        self.state.settings.save()
        preset = get_preset(self.state.settings.preset)

        if len(self.results) != len(self.files):
            self._populate_pending()
        self.progress.setRange(0, len(self.files))
        self.progress.setValue(0)
        self.start_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.save_sel_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self.worker = BatchWorker(self.files, preset, self.state.settings)
        self.worker.progress.connect(self._on_progress)
        self.worker.file_done.connect(self._on_file_done)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _cancel(self):
        if self.worker:
            self.worker.cancel()

    def _on_progress(self, done, total, name):
        self.progress.setValue(done)
        self.status_lbl.setText(f"Processing {done}/{total}: {name}")

    def _on_file_done(self, res):
        row = self.row_by_src.get(res.src)
        if row is None:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.results.append(res)
            self.row_by_src[res.src] = row
            self.table.setItem(row, 0, _check_item())
            self.table.setItem(row, 1, QTableWidgetItem())
            self.table.setItem(row, 2, QTableWidgetItem(Path(res.src).name))
            self.table.setItem(row, 3, QTableWidgetItem())
            self.table.setItem(row, 4, QTableWidgetItem())
            self.table.setCellWidget(row, 5, self._actions_widget(row))
        else:
            self.results[row] = res

        pix = self._thumb_pixmap(res)
        if pix is not None:
            self.table.item(row, 1).setIcon(QIcon(pix))
        st = self.table.item(row, 3)
        st.setText(res.status.upper())
        st.setForeground(_status_color(res.status))
        self.table.item(row, 4).setText(", ".join(res.flags))

    def _on_done(self, n_ok, n_warn, n_flag):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        enabled = any(r is not None for r in self.results)
        self.save_btn.setEnabled(enabled)
        self.save_sel_btn.setEnabled(enabled)
        self.status_lbl.setText(
            f"Processed — {n_ok} clean, {n_warn} warnings, {n_flag} flagged. "
            "Save all, or select rows and Save selected.")

    def _save_all(self):
        self._save_rows(range(len(self.results)))

    def _checked_rows(self):
        rows = [r for r in range(self.table.rowCount())
                if (it := self.table.item(r, 0)) is not None
                and it.checkState() == Qt.CheckState.Checked]
        if not rows:  # fall back to highlighted rows if nothing is ticked
            rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        return rows

    def _save_selected(self):
        rows = self._checked_rows()
        if not rows:
            QMessageBox.information(self, "No selection",
                                   "Tick the photos you want (checkbox on the left), "
                                   "then Save selected.")
            return
        self._save_rows(rows)

    def _save_rows(self, rows):
        if not any(0 <= r < len(self.results) and self.results[r] is not None for r in rows):
            QMessageBox.information(self, "Nothing to save", "Process photos first (click Start).")
            return
        preset = get_preset(self.state.settings.preset)
        out_dir = Path(self._ensure_out())
        ext = EXT.get(self.state.settings.output_format.upper(), ".jpg")
        flagged_dir = out_dir / "flagged photos"
        saved = flagged = 0
        for r in rows:
            res = self.results[r]
            if res is None:
                continue
            src = Path(res.src)
            if res.cropped is not None and res.status != "flagged":
                out_path = out_dir / (src.stem + ext)
                save_output(res.cropped, out_path, preset, self.state.settings)
                res.output_path = str(out_path)
                saved += 1
            else:
                flagged_dir.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src, flagged_dir / src.name)
                except OSError:
                    pass
                flagged += 1
        msg = f"Saved {saved} passport photo(s) to:\n{out_dir}"
        if flagged:
            msg += f"\n\n{flagged} flagged original(s) copied to:\n{flagged_dir}"
        QMessageBox.information(self, "Saved", msg)

    # --- preview & edit ---------------------------------------------------
    def _src_for_row(self, row) -> str:
        res = self.results[row]
        return res.src if res is not None else str(self.files[row])

    def _preview_row(self, row, _col=0):
        res = self.results[row]
        if res is not None and res.cropped is not None:
            bgr, sub, path = res.cropped, res.status.upper(), res.output_path
        else:
            path = self._src_for_row(row)
            bgr = _scaled_h(load_bgr(path), 900)
            sub = "Pending — original" if res is None else \
                "Flagged — original (" + ", ".join(res.flags) + ")"
        ImagePreviewDialog(bgr, Path(self._src_for_row(row)).name, sub, path, self).exec()

    def _analyzer(self) -> FaceAnalyzer:
        if self._analyzer_cache is None:
            self._analyzer_cache = FaceAnalyzer()
        return self._analyzer_cache

    def _edit_row(self, row):
        src = self._src_for_row(row)
        preset = get_preset(self.state.settings.preset)
        full = process_image(src, preset, self._analyzer(), self.state.settings,
                             keep_image=True)
        if full.image is None or full.crop is None:
            QMessageBox.warning(self, "Cannot edit", "No face/crop available to edit.")
            return
        dlg = ManualCropDialog(full.image, full.crop, preset, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_bgr is not None:
            if self.results[row] is None:
                self.results[row] = full
            self.results[row].cropped = dlg.result_bgr
            self.results[row].status = "edited"
            self.results[row].output_path = None  # written on Save all
            self.table.item(row, 3).setText("EDITED")
            self.table.item(row, 3).setForeground(_status_color("ok"))
            self.table.item(row, 4).setText("")
            self.table.item(row, 1).setIcon(QIcon(bgr_to_pixmap(thumbnail(dlg.result_bgr, THUMB + 24))))
            self.save_btn.setEnabled(True)
            self.save_sel_btn.setEnabled(True)

    def _actions_widget(self, row) -> QWidget:
        view = QPushButton("View")
        view.setMinimumWidth(72)
        view.clicked.connect(lambda _=False, r=row: self._preview_row(r))
        edit = QPushButton("Edit")
        edit.setMinimumWidth(72)
        edit.clicked.connect(lambda _=False, r=row: self._edit_row(r))
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)
        lay.addWidget(view)
        lay.addWidget(edit)
        return w

    def _thumb_pixmap(self, res) -> QPixmap | None:
        if res.cropped is not None:
            return bgr_to_pixmap(thumbnail(res.cropped, THUMB + 24))
        return _fast_thumb(Path(res.src), THUMB + 24)


def _check_item() -> QTableWidgetItem:
    """A centered, tickable checkbox cell for row selection."""
    it = QTableWidgetItem()
    it.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
    it.setCheckState(Qt.CheckState.Unchecked)
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


def _fast_thumb(path, box) -> QPixmap | None:
    """Quick thumbnail of a source image (JPEG draft decode keeps it fast)."""
    try:
        im = Image.open(path)
        im.draft("RGB", (box * 3, box * 3))
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((box, box))
        return bgr_to_pixmap(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
    except Exception:
        return None


def _scaled_h(bgr: np.ndarray, max_h: int) -> np.ndarray:
    h, w = bgr.shape[:2]
    if h <= max_h:
        return bgr
    s = max_h / h
    return cv2.resize(bgr, (int(w * s), max_h))


def _status_color(status):
    return {
        "ok": QColor(20, 140, 40),
        "edited": QColor(20, 140, 40),
        "warning": QColor(180, 120, 0),
        "flagged": QColor(190, 30, 30),
    }.get(status, QColor(0, 0, 0))
