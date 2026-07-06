"""Helpers for building synthetic objects in unit tests."""

from passport_cropper.detect import Face
from passport_cropper.presets import Preset


def make_preset(head_fraction=0.5, top_margin=0.1, output_px=(822, 1050)) -> Preset:
    return Preset(
        key="test", label="Test", width_mm=35, height_mm=45, dpi=600,
        output_px=output_px, head_fraction=head_fraction, top_margin=top_margin,
    )


def make_face(
    eye_y=300.0, chin_y=400.0, crown_y=200.0, center_x=400.0,
    roll=0.0, yaw=0.0, pitch=0.0, eye_open=0.3, mouth_open=0.1, body_below=0.8,
) -> Face:
    return Face(
        left_eye=(center_x - 10, eye_y), right_eye=(center_x + 10, eye_y),
        eye_mid=(center_x, eye_y), chin=(center_x, chin_y), crown=(center_x, crown_y),
        nose=(center_x, (eye_y + chin_y) / 2),
        box=(center_x - 60, crown_y, center_x + 60, chin_y),
        roll_deg=roll, yaw_deg=yaw, pitch_deg=pitch,
        body_below=body_below, eye_open=eye_open, mouth_open=mouth_open,
    )
