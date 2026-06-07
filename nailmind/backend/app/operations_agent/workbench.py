"""Today workbench aggregation for the operations homepage."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app import models
from app.operations_agent.design_signals import find_high_tryon_low_booking_designs


def _booking_card(db: Session, booking: models.BookingIntent) -> Dict[str, Any]:
    try_on = (
        db.query(models.TryOnRecord)
        .filter(models.TryOnRecord.id == booking.try_on_record_id)
        .first()
    )
    design_name = try_on.nail_design.name if try_on and try_on.nail_design else "未知款式"
    return {
        "id": f"booking_{booking.id}",
        "type": "booking_followup",
        "priority": "high",
        "title": f"跟进预约意向：{design_name}",
        "description": "用户已提交预约意向，需要商家尽快确认时间和服务细节。",
        "metric": "待确认",
        "target_url": "/merchant/bookings",
        "created_at": booking.created_at.isoformat() if booking.created_at else None,
    }


def _conversion_gap_card(item: Dict[str, Any]) -> Dict[str, Any]:
    design = item["design"]
    signals = item["signals"]
    rates = item["rates"]
    return {
        "id": f"conversion_gap_{design['id']}",
        "type": "conversion_gap",
        "priority": "high" if signals["booking_count"] == 0 else "medium",
        "title": f"修复转化断层：{design['name']}",
        "description": item["reason"],
        "metric": f"试戴 {signals['try_on_count']} 次，预约率 {rates['try_on_to_booking_rate']}%",
        "target_url": "/admin/assistant",
        "created_at": datetime.now().isoformat(),
    }


def _suggestion_card(suggestion: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": f"suggestion_{suggestion['id']}",
        "type": "suggestion_review",
        "priority": suggestion.get("priority", "medium"),
        "title": suggestion.get("title", "处理运营建议"),
        "description": suggestion.get("reason") or suggestion.get("description") or "建议中心有待确认动作。",
        "metric": "待采纳",
        "target_url": "/admin/suggestions",
        "created_at": suggestion.get("created_at"),
    }


def build_today_workbench(db: Session) -> Dict[str, Any]:
    pending_bookings = (
        db.query(models.BookingIntent)
        .filter(models.BookingIntent.status == "pending")
        .order_by(models.BookingIntent.created_at.desc())
        .limit(5)
        .all()
    )
    conversion_gaps = find_high_tryon_low_booking_designs(db=db, limit=3)

    from app.routers.operations import get_overview, get_suggestions

    overview = get_overview(db=db).model_dump()
    suggestions = get_suggestions(status="pending", limit=3, db=db)

    action_cards: List[Dict[str, Any]] = []
    action_cards.extend(_booking_card(db, booking) for booking in pending_bookings)
    action_cards.extend(_conversion_gap_card(item) for item in conversion_gaps)
    action_cards.extend(_suggestion_card(suggestion) for suggestion in suggestions[:3])

    priority_order = {"high": 0, "medium": 1, "low": 2}
    type_order = {"booking_followup": 0, "conversion_gap": 1, "suggestion_review": 2}
    action_cards.sort(
        key=lambda card: (
            type_order.get(card["type"], 9),
            priority_order.get(card["priority"], 3),
        )
    )

    return {
        "summary": {
            "today_try_ons": overview["today_try_ons"],
            "today_favorites": overview["today_favorites"],
            "today_booking_intents": overview["today_booking_intents"],
            "hot_designs_count": overview["hot_designs_count"],
            "pending_booking_count": len(pending_bookings),
            "conversion_gap_count": len(conversion_gaps),
            "pending_suggestion_count": len(suggestions),
        },
        "action_cards": action_cards[:8],
        "trending_styles": overview["trending_styles"],
    }
