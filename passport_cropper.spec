# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — builds a one-folder desktop app that bundles the ML
models and the default presets. Produces PassportCropper.app on macOS and a
PassportCropper folder with PassportCropper.exe on Windows.

Build:  pyinstaller passport_cropper.spec
"""

import sys
from PyInstaller.utils.hooks import collect_all

ICON = "assets/AppIcon.icns" if sys.platform == "darwin" else "assets/AppIcon.ico"
datas = [("models", "models"), ("presets.json", "."), ("assets", "assets")]
binaries = []
hiddenimports = []

# MediaPipe ships model/graph data files and native libs that must be collected.
for pkg in ("mediapipe",):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["run_app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Gowri Studio",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Gowri Studio",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Gowri Studio.app",
        icon="assets/AppIcon.icns",
        bundle_identifier="com.gowristudio.app",
    )
