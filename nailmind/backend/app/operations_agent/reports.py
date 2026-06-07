"""Read-only report aggregations for the operations agent."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app import models
from app.operations_agent.design_signals import COMPLETED_TRYON_STATUSES
from app.services.design_visual_tags import design_to_effective_tags


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 1)


def _safe_window_days(days: int) -> int:
    return max(1, min(int(days or 7), 90))


def _counter_or_real(counter_value: Any, real_count: int) -> int:
    try:
        parsed = int(counter_value or 0)
    except (TypeError, ValueError):
        parsed = 0
    return max(parsed, real_count)


def _design_summary(design: models.NailDesign) -> Dict[str, Any]:
    tags = design_to_effective_tags(design)
    return {
        "id": design.id,
        "name": design.name,
        "image_url": design.image_url,
        "style_tags": tags["style_tags"],
        "color_tags": tags["color_tags"],
        "scene_tags": tags["scene_tags"],
        "is_hot": bool(design.is_hot),
        "status": design.status,
    }


def _period_start(days: int) -> datetime:
    return datetime.now() - timedelta(days=_safe_window_days(days))


def _recent_try_ons(db: Session, days: int):
    return (
        db.query(models.TryOnRecord)
        .filter(models.TryOnRecord.created_at >= _period_start(days))
        .all()
    )


def _count_tags(records: list[models.TryOnRecord], field: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for record in records:
        if not record.nail_design:
            continue
        for tag in design_to_effective_tags(record.nail_design).get(field) or []:
            counts[tag] = counts.get(tag, 0) + 1
    return [
        {"tag": tag, "try_ons": count}
        for tag, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:8]
    ]


def _design_metrics(db: Session, design: models.NailDesign, days: int) -> Dict[str, Any]:
    start = _period_start(days)
    try_on_query = db.query(models.TryOnRecord).filter(models.TryOnRecord.nail_design_id == design.id)
    period_try_on_query = try_on_query.filter(models.TryOnRecord.created_at >= start)
    completed_query = try_on_query.filter(models.TryOnRecord.status.in_(COMPLETED_TRYON_STATUSES))
    real_try_ons = completed_query.count()
    real_favorites = db.query(models.Favorite).filter(models.Favorite.nail_design_id == design.id).count()
    real_bookings = db.query(models.BookingIntent).filter(models.BookingIntent.nail_design_id == design.id).count()

    try_ons = _counter_or_real(design.try_on_count, real_try_ons)
    favorites = _counter_or_real(design.favorite_count, real_favorites)
    bookings = _counter_or_real(design.booking_count, real_bookings)
    period_try_ons = period_try_on_query.count()
    period_favorites = (
        db.query(models.Favorite)
        .filter(models.Favorite.nail_design_id == design.id, models.Favorite.created_at >= start)
        .count()
    )
    period_bookings = (
        db.query(models.BookingIntent)
        .filter(models.BookingIntent.nail_design_id == design.id, models.BookingIntent.created_at >= start)
        .count()
    )

    return {
        "view_count": int(design.view_count or 0),
        "try_on_count": try_ons,
        "favorite_count": favorites,
        "booking_count": bookings,
        "period_try_ons": period_try_ons,
        "period_favorites": period_favorites,
        "period_bookings": period_bookings,
        "try_on_to_favorite_rate": _percent(favorites, try_ons),
        "try_on_to_booking_rate": _percent(bookings, try_ons),
        "view_to_try_on_rate": _percent(try_ons, int(design.view_count or 0)),
    }


def build_weekly_report(db: Session, days: int = 7) -> Dict[str, Any]:
    period_days = _safe_window_days(days)
    start = _period_start(period_days)
    records = _recent_try_ons(db, period_days)
    completed_records = [record for record in records if record.status in COMPLETED_TRYON_STATUSES]

    favorite_count = (
        db.query(models.Favorite)
        .filter(models.Favorite.created_at >= start)
        .count()
    )
    booking_count = (
        db.query(models.BookingIntent)
        .filter(models.BookingIntent.created_at >= start)
        .count()
    )
    unique_users = {record.user_id for record in records if record.user_id}

    design_counts: dict[int, int] = {}
    for record in records:
        if record.nail_design_id:
            design_counts[record.nail_design_id] = design_counts.get(record.nail_design_id, 0) + 1

    top_designs: list[dict[str, Any]] = []
    for design_id, count in sorted(design_counts.items(), key=lambda item: item[1], reverse=True)[:5]:
        design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
        if design:
            top_designs.append(
                {
                    "design": _design_summary(design),
                    "period_try_ons": count,
                    "metrics": _design_metrics(db, design, period_days),
                }
            )

    top_design_name = top_designs[0]["design"]["name"] if top_designs else "暂无明显领先款"
    top_style = _count_tags(records, "style_tags")
    top_style_name = top_style[0]["tag"] if top_style else "暂无明显风格"

    recommendations: list[dict[str, Any]] = []
    if top_designs:
        recommendations.append(
            {
                "action": f"复盘并加推 {top_design_name}",
                "reason": f"近 {period_days} 天试戴量领先，可作为下周推荐位候选。",
                "priority": "high",
                "target": top_design_name,
                "requires_confirmation": True,
            }
        )
    if booking_count < max(1, len(completed_records) * 0.08):
        recommendations.append(
            {
                "action": "检查试戴结果页预约承接",
                "reason": "预约量相对试戴量偏弱，需要复盘价格、档期和预约入口表达。",
                "priority": "medium",
                "requires_confirmation": True,
            }
        )

    return {
        "period_days": period_days,
        "period": {
            "start_at": start.isoformat(),
            "end_at": datetime.now().isoformat(),
        },
        "metrics": {
            "try_ons": len(records),
            "completed_try_ons": len(completed_records),
            "favorites": favorite_count,
            "bookings": booking_count,
            "unique_users": len(unique_users),
            "try_on_to_favorite_rate": _percent(favorite_count, len(completed_records)),
            "try_on_to_booking_rate": _percent(booking_count, len(completed_records)),
        },
        "top_styles": top_style,
        "top_colors": _count_tags(records, "color_tags"),
        "top_designs": top_designs,
        "summary": (
            f"近 {period_days} 天共产生 {len(records)} 次试戴、{favorite_count} 次收藏、"
            f"{booking_count} 次预约。领先款式是 {top_design_name}，领先风格是 {top_style_name}。"
        ),
        "recommendations": recommendations,
    }


def build_recommendation_slot_plan(db: Session, limit: int = 5) -> Dict[str, Any]:
    safe_limit = max(1, min(int(limit or 5), 20))
    designs = db.query(models.NailDesign).filter(models.NailDesign.status == "active").all()
    scored: list[dict[str, Any]] = []

    for design in designs:
        metrics = _design_metrics(db, design, days=7)
        score = (
            metrics["period_try_ons"] * 3
            + metrics["period_favorites"] * 5
            + metrics["period_bookings"] * 10
            + metrics["try_on_to_booking_rate"] * 0.3
        )
        scored.append({"design": design, "metrics": metrics, "score": round(score, 1)})

    promote_items = [
        item
        for item in scored
        if not item["design"].is_hot
        and (item["metrics"]["period_try_ons"] >= 5 or item["metrics"]["booking_count"] >= 1)
    ]
    demote_items = [
        item
        for item in scored
        if item["design"].is_hot
        and (
            item["metrics"]["period_try_ons"] <= 3
            or item["metrics"]["try_on_to_booking_rate"] <= 5
        )
    ]

    promote_recommendations: list[dict[str, Any]] = []
    for item in sorted(promote_items, key=lambda value: value["score"], reverse=True):
        design = item["design"]
        metrics = item["metrics"]
        promote_recommendations.append(
            {
                "slot_action": "promote",
                "action": f"上调推荐位：{design.name}",
                "design": _design_summary(design),
                "metrics": metrics,
                "score": item["score"],
                "reason": (
                    f"近 7 天试戴 {metrics['period_try_ons']} 次，"
                    f"预约 {metrics['period_bookings']} 次，具备加推观察价值。"
                ),
                "priority": "high",
                "requires_confirmation": True,
            }
        )

    demote_recommendations: list[dict[str, Any]] = []
    for item in sorted(demote_items, key=lambda value: value["score"]):
        design = item["design"]
        metrics = item["metrics"]
        demote_recommendations.append(
            {
                "slot_action": "demote",
                "action": f"下调推荐位：{design.name}",
                "design": _design_summary(design),
                "metrics": metrics,
                "score": item["score"],
                "reason": (
                    f"当前仍是热门位款式，但近 7 天试戴仅 {metrics['period_try_ons']} 次，"
                    "继续占位会挤压高潜款曝光。"
                ),
                "priority": "medium",
                "requires_confirmation": True,
            }
        )

    recommendations: list[dict[str, Any]] = []
    if promote_recommendations:
        recommendations.append(promote_recommendations[0])
    if safe_limit > 1 and demote_recommendations:
        recommendations.append(demote_recommendations[0])

    occupied_ids = {item["design"]["id"] for item in recommendations}
    remaining_recommendations = [
        item
        for item in [*promote_recommendations[1:], *demote_recommendations[1:]]
        if item["design"]["id"] not in occupied_ids
    ]
    for item in remaining_recommendations:
        if len(recommendations) >= safe_limit:
            break
        recommendations.append(item)
        occupied_ids.add(item["design"]["id"])

    for item in sorted(scored, key=lambda value: value["score"], reverse=True):
        if len(recommendations) >= safe_limit:
            break
        design = item["design"]
        if design.id in occupied_ids:
            continue
        recommendations.append(
            {
                "slot_action": "observe",
                "action": f"继续观察：{design.name}",
                "design": _design_summary(design),
                "metrics": item["metrics"],
                "score": item["score"],
                "reason": "当前信号不足以直接上调或下调，保留观察即可。",
                "priority": "low",
                "requires_confirmation": True,
            }
        )

    promote_count = len([item for item in recommendations if item["slot_action"] == "promote"])
    demote_count = len([item for item in recommendations if item["slot_action"] == "demote"])
    return {
        "summary": f"生成 {len(recommendations)} 条推荐位计划：上调 {promote_count} 条，下调 {demote_count} 条。",
        "recommendations": recommendations,
    }
