"""Desktop app entry point (used by PyInstaller and for `python run_app.py`)."""

from passport_cropper.gui.app import run

if __name__ == "__main__":
    raise SystemExit(run())
