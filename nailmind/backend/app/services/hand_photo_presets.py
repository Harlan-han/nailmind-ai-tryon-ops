"""Official hand photo presets for no-upload try-on demos."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HandPhotoPreset:
    id: str
    name: str
    image_url: str
    tags: list[str]
    crop_ratio: str = "4:5"


HAND_UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads" / "hands"

PRESET_HAND_PHOTOS: tuple[HandPhotoPreset, ...] = tuple(
    HandPhotoPreset(
        id=f"official-hand-{index:02d}",
        name=f"官方预设 {index:02d}",
        image_url=f"/uploads/hands/hand_{index:02d}.jpg",
        tags=["官方预设", "快速体验", "自然光"],
    )
    for index in range(1, 14)
)


def list_available_hand_photo_presets() -> list[HandPhotoPreset]:
    return [
        preset
        for preset in PRESET_HAND_PHOTOS
        if (HAND_UPLOADS_DIR / Path(preset.image_url).name).is_file()
    ]


def get_hand_photo_preset(preset_id: str) -> HandPhotoPreset | None:
    for preset in list_available_hand_photo_presets():
        if preset.id == preset_id:
            return preset
    return None
