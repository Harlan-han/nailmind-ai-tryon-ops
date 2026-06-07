"""Design-level conversion signals for the operations agent."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app import models
from app.services.design_visual_tags import design_to_effective_tags


COMPLETED_TRYON_STATUSES = ("completed",)


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _counter_or_real(counter_value: Any, real_count: int) -> int:
    try:
        parsed = int(counter_value or 0)
    except (TypeError, ValueError):
        parsed = 0
    return max(parsed, real_count)


def _design_summary(design: models.NailDesign) -> Dict[str, Any]:
    effective = design_to_effective_tags(design)
    return {
        "id": design.id,
        "name": design.name,
        "image_url": design.image_url,
        "style_tags": effective["style_tags"],
        "color_tags": effective["color_tags"],
        "scene_tags": effective["scene_tags"],
        "status": design.status,
        "is_hot": bool(design.is_hot),
    }


def analyze_design_performance(db: Session, design_id: int) -> Dict[str, Any]:
    design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
    if not design:
        raise ValueError(f"Design not found: {design_id}")

    try_on_query = db.query(models.TryOnRecord).filter(models.TryOnRecord.nail_design_id == design.id)
    completed_try_on_query = try_on_query.filter(models.TryOnRecord.status.in_(COMPLETED_TRYON_STATUSES))
    real_try_on_count = completed_try_on_query.count()
    real_favorite_count = db.query(models.Favorite).filter(models.Favorite.nail_design_id == design.id).count()
    real_booking_count = db.query(models.BookingIntent).filter(models.BookingIntent.nail_design_id == design.id).count()

    try_on_count = _counter_or_real(design.try_on_count, real_try_on_count)
    favorite_count = _counter_or_real(design.favorite_count, real_favorite_count)
    booking_count = _counter_or_real(design.booking_count, real_booking_count)
    view_count = int(design.view_count or 0)

    recent_start = datetime.now() - timedelta(days=7)
    recent_try_on_count = completed_try_on_query.filter(models.TryOnRecord.created_at >= recent_start).count()
    converted_try_ons = (
        completed_try_on_query.filter(models.TryOnRecord.has_booking_intent == True)
        .order_by(models.TryOnRecord.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "design": _design_summary(design),
        "signals": {
            "view_count": view_count,
            "try_on_count": try_on_count,
            "favorite_count": favorite_count,
            "booking_count": booking_count,
            "recent_7d_try_on_count": recent_try_on_count,
        },
        "rates": {
            "view_to_try_on_rate": _percent(try_on_count, view_count),
            "try_on_to_favorite_rate": _percent(favorite_count, try_on_count),
            "try_on_to_booking_rate": _percent(booking_count, try_on_count),
            "favorite_to_booking_rate": _percent(booking_count, favorite_count),
        },
        "converted_try_on_images": [
            {
                "try_on_id": item.id,
                "result_image_url": item.result_image_url,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in converted_try_ons
            if item.result_image_url
        ],
    }


def explain_hot_design(db: Session, design_id: int) -> Dict[str, Any]:
    performance = analyze_design_performance(db, design_id)
    signals = performance["signals"]
    rates = performance["rates"]
    reasons: List[str] = []

    if signals["try_on_count"] >= 20:
        reasons.append("试戴量已经达到可推广观察线")
    if signals["recent_7d_try_on_count"] >= 5:
        reasons.append("近 7 天仍有持续试戴热度")
    if rates["try_on_to_favorite_rate"] >= 20:
        reasons.append("试戴后的收藏率较高，说明用户审美认可")
    if rates["try_on_to_booking_rate"] >= 8:
        reasons.append("试戴后预约转化可观，具备商业化价值")
    if not reasons:
        reasons.append("当前更像潜力款，需要继续观察试戴和预约信号")

    return {
        **performance,
        "hot_reasons": reasons,
        "recommendation": "优先进入推荐位观察" if len(reasons) >= 2 else "先保留在候选池继续观察",
    }


def find_high_tryon_low_booking_designs(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    designs = db.query(models.NailDesign).filter(models.NailDesign.status == "active").all()
    items: List[Dict[str, Any]] = []

    for design in designs:
        data = analyze_design_performance(db, design.id)
        signals = data["signals"]
        rates = data["rates"]
        if signals["try_on_count"] >= 10 and rates["try_on_to_booking_rate"] <= 10:
            items.append(
                {
                    "design": data["design"],
                    "alert_type": "high_tryon_low_booking",
                    "signals": signals,
                    "rates": rates,
                    "reason": "试戴兴趣存在，但预约承接弱，需要检查价格、预约入口或试戴效果可信度。",
                    "suggestion": "降低推荐位权重或增加预约引导文案，并追踪 24 小时预约变化。",
                }
            )

    items.sort(key=lambda item: (item["signals"]["try_on_count"], -item["signals"]["booking_count"]), reverse=True)
    return items[:limit]


def find_high_favorite_low_booking_designs(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    designs = db.query(models.NailDesign).filter(models.NailDesign.status == "active").all()
    items: List[Dict[str, Any]] = []

    for design in designs:
        data = analyze_design_performance(db, design.id)
        signals = data["signals"]
        rates = data["rates"]
        if signals["favorite_count"] >= 3 and rates["favorite_to_booking_rate"] <= 25:
            items.append(
                {
                    "design": data["design"],
                    "alert_type": "high_favorite_low_booking",
                    "signals": signals,
                    "rates": rates,
                    "reason": "用户愿意收藏但没有继续预约，可能卡在价格、档期、门店信任或行动入口。",
                    "suggestion": "对这类款增加限时预约提示、门店案例说明或客服跟进入口。",
                }
            )

    items.sort(key=lambda item: (item["signals"]["favorite_count"], -item["signals"]["booking_count"]), reverse=True)
    return items[:limit]


def find_converted_tryon_images(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    records = (
        db.query(models.TryOnRecord)
        .filter(
            models.TryOnRecord.status.in_(COMPLETED_TRYON_STATUSES),
            models.TryOnRecord.has_booking_intent == True,
            models.TryOnRecord.result_image_url.isnot(None),
        )
        .order_by(models.TryOnRecord.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "try_on_id": record.id,
            "design": _design_summary(record.nail_design) if record.nail_design else None,
            "result_image_url": record.result_image_url,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
        for record in records
    ]
