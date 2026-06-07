"""Shared operations configuration backed by backend data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app import models
from app.services.design_visual_tags import collect_visual_tags


CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "operations_config.json"

DEFAULT_RULES = {
    "hotThreshold": 50,
    "newThreshold": 7,
    "trendingDays": 7,
    "designsPerPage": 20,
    "maxCandidates": 10,
    "enableAiInsights": True,
    "enableNotifications": True,
}

TAG_FIELD_MAP = {
    "styleTags": "style_tags",
    "colorTags": "color_tags",
    "sceneTags": "scene_tags",
}


def _dedupe_tags(values: Any) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        tag = str(value).strip()
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def _int_value(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


def _bool_value(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def load_saved_operations_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_operations_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_operations_config(db: Session, saved_config: dict[str, Any] | None = None) -> dict[str, Any]:
    saved = saved_config or {}
    designs = db.query(models.NailDesign).filter(models.NailDesign.status == "active").all()

    config: dict[str, Any] = {}
    for api_field, design_field in TAG_FIELD_MAP.items():
        saved_tags = _dedupe_tags(saved.get(api_field))
        design_tags = collect_visual_tags(designs, design_field)
        config[api_field] = _dedupe_tags([*saved_tags, *design_tags])

    config["hotThreshold"] = _int_value(saved.get("hotThreshold"), DEFAULT_RULES["hotThreshold"], 1, 1000)
    config["newThreshold"] = _int_value(saved.get("newThreshold"), DEFAULT_RULES["newThreshold"], 1, 90)
    config["trendingDays"] = _int_value(saved.get("trendingDays"), DEFAULT_RULES["trendingDays"], 1, 90)
    config["designsPerPage"] = _int_value(saved.get("designsPerPage"), DEFAULT_RULES["designsPerPage"], 5, 100)
    config["maxCandidates"] = _int_value(saved.get("maxCandidates"), DEFAULT_RULES["maxCandidates"], 1, 50)
    config["enableAiInsights"] = _bool_value(saved.get("enableAiInsights"), DEFAULT_RULES["enableAiInsights"])
    config["enableNotifications"] = _bool_value(saved.get("enableNotifications"), DEFAULT_RULES["enableNotifications"])
    return config


def get_operations_config(db: Session) -> dict[str, Any]:
    return build_operations_config(db, load_saved_operations_config())


def update_operations_config(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "styleTags": _dedupe_tags(payload.get("styleTags")),
        "colorTags": _dedupe_tags(payload.get("colorTags")),
        "sceneTags": _dedupe_tags(payload.get("sceneTags")),
        "hotThreshold": _int_value(payload.get("hotThreshold"), DEFAULT_RULES["hotThreshold"], 1, 1000),
        "newThreshold": _int_value(payload.get("newThreshold"), DEFAULT_RULES["newThreshold"], 1, 90),
        "trendingDays": _int_value(payload.get("trendingDays"), DEFAULT_RULES["trendingDays"], 1, 90),
        "designsPerPage": _int_value(payload.get("designsPerPage"), DEFAULT_RULES["designsPerPage"], 5, 100),
        "maxCandidates": _int_value(payload.get("maxCandidates"), DEFAULT_RULES["maxCandidates"], 1, 50),
        "enableAiInsights": _bool_value(payload.get("enableAiInsights"), DEFAULT_RULES["enableAiInsights"]),
        "enableNotifications": _bool_value(payload.get("enableNotifications"), DEFAULT_RULES["enableNotifications"]),
    }
    save_operations_config(normalized)
    return build_operations_config(db, normalized)
