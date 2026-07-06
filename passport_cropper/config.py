"""Application settings, persisted to settings.json.

One place for everything the Uploads/Configuration pages and the CLI share:
output format/folder, tilt thresholds, quality-check toggles, and optional
file-size targeting.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .resources import data_dir

DEFAULT_SETTINGS_PATH = data_dir() / "settings.json"

# Quality checks and their default thresholds. Each check can be turned off or
# set to "warn" (crop is still produced) or "fail" (no crop; goes to review).
DEFAULT_CHECKS: dict[str, dict] = {
    "insufficient_margin": {"enabled": True, "level": "fail"},
    "low_resolution": {"enabled": True, "level": "warn", "min_scale": 1.0},
    "not_facing_forward": {"enabled": True, "level": "warn"},
    "excessive_tilt": {"enabled": True, "level": "warn"},
    "eyes_closed": {"enabled": True, "level": "warn", "ear_threshold": 0.15},
    "mouth_open": {"enabled": True, "level": "warn", "open_threshold": 0.35},
    "uneven_lighting": {"enabled": True, "level": "warn", "ratio_threshold": 0.35},
}


@dataclass
class TiltSettings:
    auto_straighten: bool = True
    max_roll: float = 15.0
    max_yaw: float = 10.0
    max_pitch: float = 10.0


@dataclass
class Settings:
    preset: str = "india_35x45"
    theme: str = "light"                   # "dark" | "light"
    output_dir: str = "output"
    output_format: str = "JPEG"           # JPEG | PNG | PDF
    jpeg_quality: int = 95
    recurse: bool = False
    parallel: bool = True
    filename_pattern: str = "{name}"      # keep original name
    tilt: TiltSettings = field(default_factory=TiltSettings)
    # File-size targeting (optional). None = off. Sizes in kilobytes.
    target_kb: int | None = None
    target_kb_min: int | None = None
    checks: dict[str, dict] = field(default_factory=lambda: _clone(DEFAULT_CHECKS))

    def check(self, name: str) -> dict:
        return self.checks.get(name, DEFAULT_CHECKS.get(name, {"enabled": False}))

    # --- persistence -------------------------------------------------------
    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        d = dict(d)
        tilt = TiltSettings(**d.pop("tilt", {}))
        checks = _clone(DEFAULT_CHECKS)
        for name, cfg in d.pop("checks", {}).items():
            checks.setdefault(name, {}).update(cfg)
        known = {f for f in cls.__dataclass_fields__ if f not in ("tilt", "checks")}
        return cls(tilt=tilt, checks=checks, **{k: v for k, v in d.items() if k in known})

    def save(self, path: str | Path = DEFAULT_SETTINGS_PATH) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path = DEFAULT_SETTINGS_PATH) -> "Settings":
        p = Path(path)
        if not p.exists():
            return cls()
        return cls.from_dict(json.loads(p.read_text()))


def _clone(checks: dict[str, dict]) -> dict[str, dict]:
    return {k: dict(v) for k, v in checks.items()}
