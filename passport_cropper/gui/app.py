"""Gowri Studio — main window (branded header + Uploads/Configuration) and startup."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton, QTabWidget,
    QVBoxLayout, QWidget,
)

from ..config import Settings
from ..presets import load_presets, sync_bundled_presets
from ..resources import bundled
from .config_page import ConfigPage
from .splash import SplashScreen
from .style import build_qss
from .uploads_page import UploadsPage

LOGO = bundled("assets", "logo.png")
WELCOME = bundled("assets", "welcome.mp4")
APP_NAME = "Gowri Studio"
TAGLINE = "Capturing Moments, Crafting Memories"


class AppState:
    """Shared settings + presets both pages read/write."""

    def __init__(self):
        self.settings = Settings.load()
        self.presets = load_presets()


def apply_theme(theme: str):
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(build_qss(theme == "dark"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1060, 800)
        self.state = AppState()

        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self._header())

        tabs = QTabWidget()
        self.uploads = UploadsPage(self.state)
        self.config = ConfigPage(self.state)
        tabs.addTab(self.uploads, "Uploads")
        tabs.addTab(self.config, "Configuration")
        v.addWidget(tabs, 1)
        self.setCentralWidget(central)

    def _header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(66)
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 10, 20, 10)

        logo = QLabel()
        pm = QPixmap(str(LOGO))
        if not pm.isNull():
            logo.setPixmap(pm.scaledToHeight(42, Qt.TransformationMode.SmoothTransformation))
        brand = QVBoxLayout()
        brand.setSpacing(0)
        name = QLabel(APP_NAME)
        name.setObjectName("brand")
        sub = QLabel(TAGLINE)
        sub.setObjectName("brandsub")
        brand.addWidget(name)
        brand.addWidget(sub)

        self.theme_btn = QPushButton(self._theme_label())
        self.theme_btn.setObjectName("themeToggle")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)

        h.addWidget(logo)
        h.addSpacing(12)
        h.addLayout(brand)
        h.addStretch(1)
        h.addWidget(self.theme_btn)
        return header

    def _theme_label(self) -> str:
        return "🌙  Dark" if self.state.settings.theme == "dark" else "☀  Light"

    def _toggle_theme(self):
        self.state.settings.theme = "light" if self.state.settings.theme == "dark" else "dark"
        self.state.settings.save()
        apply_theme(self.state.settings.theme)
        self.theme_btn.setText(self._theme_label())


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    sync_bundled_presets()      # pull in any presets added by a new version
    settings = Settings.load()
    apply_theme(settings.theme)
    icon = QIcon(str(LOGO))
    app.setWindowIcon(icon)

    win = MainWindow()
    win.setWindowIcon(icon)

    splash = SplashScreen(WELCOME)
    splash.finished.connect(win.show)
    splash.start()
    return app.exec()
