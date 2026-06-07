"""Persistent hand photo display metadata without a database migration."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CROP_RATIO = "1:1"
ALLOWED_CROP_RATIOS = {"1:1", "4:5", "3:4"}


def _state_path() -> Path:
    configured = os.getenv("HAND_PHOTO_META_STATE_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "data" / "hand_photo_meta.json"


def _load_state() -> dict[str, dict[str, str]]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(state: dict[str, dict[str, str]]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_hand_photo_meta(photo_id: int) -> dict[str, str | None]:
    state = _load_state()
    meta = state.get(str(photo_id)) or {}
    crop_ratio = meta.get("crop_ratio")
    return {
        "name": meta.get("name"),
        "crop_ratio": crop_ratio if crop_ratio in ALLOWED_CROP_RATIOS else DEFAULT_CROP_RATIO,
    }


def update_hand_photo_meta(photo_id: int, payload: dict[str, Any]) -> dict[str, str | None]:
    state = _load_state()
    current = dict(state.get(str(photo_id)) or {})

    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if name:
            current["name"] = name[:80]
        else:
            current.pop("name", None)

    if "crop_ratio" in payload:
        crop_ratio = str(payload.get("crop_ratio") or DEFAULT_CROP_RATIO).strip()
        current["crop_ratio"] = crop_ratio if crop_ratio in ALLOWED_CROP_RATIOS else DEFAULT_CROP_RATIO

    state[str(photo_id)] = current
    _save_state(state)
    return get_hand_photo_meta(photo_id)


def delete_hand_photo_meta(photo_id: int) -> None:
    state = _load_state()
    if str(photo_id) not in state:
        return
    state.pop(str(photo_id), None)
    _save_state(state)

