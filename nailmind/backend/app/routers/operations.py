"""Operations dashboard routes."""
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Annotated, Any, List
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.config import get_settings
from app import models, schemas
from app.auth import get_current_user, require_operator
from app.services.design_visual_tags import design_to_effective_tags, design_to_response
from app.services.phone import normalize_phone

router = APIRouter()

BUSINESS_TRY_ON_STATUSES = ("completed",)


def _business_try_on_query(db: Session):
    return db.query(models.TryOnRecord).filter(models.TryOnRecord.status.in_(BUSINESS_TRY_ON_STATUSES))


def _current_local_day_start_as_db_naive() -> datetime:
    """Return local-day midnight in the naive UTC format SQLite CURRENT_TIMESTAMP stores."""
    local_day_start = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    return local_day_start.astimezone(timezone.utc).replace(tzinfo=None)


def _apply_structured_suggestion(suggestion_id: str, db: Session) -> dict[str, Any]:
    """Apply safe, deterministic suggestion IDs to the user-facing distribution state."""
    action_by_prefix = {
        "hot_": ("promote_hot_design", True),
        "cold_": ("demote_hot_design", False),
    }
    for prefix, (action, is_hot) in action_by_prefix.items():
        if not suggestion_id.startswith(prefix):
            continue
        try:
            design_id = int(suggestion_id.removeprefix(prefix))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid suggestion id")

        design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail="Design not found")
        if design.status != "active":
            raise HTTPException(status_code=400, detail="Cannot apply suggestion to inactive design")

        design.is_hot = is_hot
        db.commit()
        return {
            "applied_action": action,
            "design_id": design.id,
            "is_hot": design.is_hot,
        }

    return {"applied_action": "status_only"}


def _design_tags(design: models.NailDesign | None, field: str) -> list[str]:
    if not design:
        return []
    return list(design_to_effective_tags(design).get(field) or [])


def _booking_to_followup_response(db: Session, booking: models.BookingIntent) -> dict[str, Any]:
    user = db.query(models.User).filter(models.User.id == booking.user_id).first()
    design = db.query(models.NailDesign).filter(
        models.NailDesign.id == booking.nail_design_id
    ).first()
    try_on = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.id == booking.try_on_record_id
    ).first()

    return {
        "id": booking.id,
        "user_id": booking.user_id,
        "user_name": user.nickname if user and user.nickname else f"User {booking.user_id}",
        "phone": booking.phone,
        "try_on_record_id": booking.try_on_record_id,
        "nail_design_id": booking.nail_design_id,
        "design_name": design.name if design else "Unknown design",
        "design_image_url": design.image_url if design else None,
        "try_on_result_image_url": try_on.result_image_url if try_on else None,
        "preferred_date": booking.preferred_date.isoformat() if booking.preferred_date else None,
        "notes": booking.notes,
        "status": booking.status,
        "created_at": booking.created_at.isoformat() if booking.created_at else None,
    }


def _extract_feishu_sender(payload: dict[str, Any]) -> str:
    event = payload.get("event") or {}
    sender = event.get("sender") or {}
    sender_id = sender.get("sender_id") or {}
    return (
        sender_id.get("open_id")
        or sender_id.get("user_id")
        or sender.get("sender_id")
        or payload.get("sender")
        or "feishu_operator"
    )


def _extract_feishu_text(payload: dict[str, Any]) -> str:
    event = payload.get("event") or {}
    message = event.get("message") or {}
    if message.get("message_type") and message.get("message_type") != "text":
        return ""

    content = message.get("content")
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return content.strip()
        return str(parsed.get("text") or "").strip()
    if isinstance(content, dict):
        return str(content.get("text") or "").strip()
    return str(payload.get("text") or payload.get("message") or "").strip()


def _format_relative_time(created_at: datetime | None) -> str:
    if not created_at:
        return ""

    delta = datetime.now() - created_at.replace(tzinfo=None)
    if delta.days > 0:
        return f"{delta.days}天前"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours}小时前"
    minutes = delta.seconds // 60
    if minutes > 0:
        return f"{minutes}分钟前"
    return "刚刚"


def _merchant_activity(
    action: str,
    design: models.NailDesign | None,
    created_at: datetime | None,
    event_key: str | None = None,
) -> dict[str, Any]:
    return {
        "event_key": event_key or f"activity_{action}_{design.id if design else 'unknown'}_{created_at.isoformat() if created_at else 'unknown'}",
        "action": action,
        "detail": design.name if design else "未知款式",
        "time": _format_relative_time(created_at),
        "created_at": created_at.isoformat() if created_at else None,
    }


def _try_on_activity(try_on: models.TryOnRecord) -> dict[str, Any]:
    if try_on.status == "failed":
        activity = _merchant_activity("试戴失败", try_on.nail_design, try_on.completed_at or try_on.created_at)
        if try_on.error_message:
            activity["detail"] = f"{activity['detail']} - {try_on.error_message[:120]}"
        return activity
    return _merchant_activity("用户试戴", try_on.nail_design, try_on.created_at)


BOOKING_STATUS_TRANSITIONS = {
    "pending": {"contacted", "cancelled"},
    "contacted": {"confirmed", "cancelled"},
    "confirmed": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def _validate_booking_status_transition(current_status: str, next_status: str) -> None:
    allowed_next_statuses = BOOKING_STATUS_TRANSITIONS.get(current_status)
    if allowed_next_statuses is None or next_status not in allowed_next_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid booking status transition: {current_status} -> {next_status}",
        )


@router.get("/overview", response_model=schemas.TrendOverview)
def get_overview(db: Session = Depends(get_db), _operator: models.User = Depends(require_operator)):
    """Get today's operations overview."""
    today = _current_local_day_start_as_db_naive()

    # Today's stats
    today_try_ons = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= today
    ).count()

    today_favorites = db.query(models.Favorite).filter(
        models.Favorite.created_at >= today
    ).count()

    today_bookings = db.query(models.BookingIntent).filter(
        models.BookingIntent.created_at >= today
    ).count()

    # Hot designs count
    hot_count = db.query(models.NailDesign).filter(
        models.NailDesign.is_hot == True,
        models.NailDesign.status == "active"
    ).count()

    # Trending styles (last 7 days)
    week_ago = today - timedelta(days=7)
    recent_try_ons = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= week_ago
    ).all()

    style_counts = {}
    for try_on in recent_try_ons:
        for tag in _design_tags(try_on.nail_design, "style_tags"):
            style_counts[tag] = style_counts.get(tag, 0) + 1

    trending_styles = [
        {"style": k, "count": v}
        for k, v in sorted(style_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    return schemas.TrendOverview(
        today_try_ons=today_try_ons,
        today_favorites=today_favorites,
        today_booking_intents=today_bookings,
        hot_designs_count=hot_count,
        trending_styles=trending_styles
    )


@router.get("/merchant-overview", response_model=schemas.MerchantOverview)
def get_merchant_overview(
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Get live merchant-facing performance metrics."""
    today = _current_local_day_start_as_db_naive()

    total_designs = db.query(models.NailDesign).count()
    active_designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active"
    ).count()
    total_views = db.query(func.sum(models.NailDesign.view_count)).scalar() or 0
    total_try_ons = _business_try_on_query(db).count()
    failed_try_ons = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.status == "failed"
    ).count()
    total_favorites = db.query(models.Favorite).count()
    recent_bookings = db.query(models.BookingIntent).filter(
        models.BookingIntent.created_at >= today
    ).count()
    conversion_rate = round(total_favorites / total_try_ons * 100, 1) if total_try_ons else 0.0

    hot_designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active"
    ).order_by(
        models.NailDesign.try_on_count.desc(),
        models.NailDesign.favorite_count.desc(),
        models.NailDesign.id.asc(),
    ).limit(5).all()

    activities: list[dict[str, Any]] = []
    for booking in db.query(models.BookingIntent).order_by(
        models.BookingIntent.created_at.desc()
    ).limit(5).all():
        design = db.query(models.NailDesign).filter(models.NailDesign.id == booking.nail_design_id).first()
        activity = _merchant_activity("提交预约", design, booking.created_at)
        activity["event_key"] = f"booking_{booking.id}"
        activity["detail"] = f"{activity['detail']} - {booking.phone}"
        activities.append(activity)

    for favorite in db.query(models.Favorite).order_by(
        models.Favorite.created_at.desc()
    ).limit(5).all():
        design = db.query(models.NailDesign).filter(models.NailDesign.id == favorite.nail_design_id).first()
        activities.append(_merchant_activity("收藏款式", design, favorite.created_at))

        activities[-1]["event_key"] = f"favorite_{favorite.id}"

    activity_try_on_statuses = (*BUSINESS_TRY_ON_STATUSES, "failed")
    for try_on in db.query(models.TryOnRecord).filter(
        models.TryOnRecord.status.in_(activity_try_on_statuses)
    ).order_by(
        models.TryOnRecord.created_at.desc()
    ).limit(5).all():
        activity = _try_on_activity(try_on)
        activity["event_key"] = f"tryon_{try_on.id}"
        activities.append(activity)

    activities.sort(key=lambda item: item["created_at"] or "", reverse=True)

    return schemas.MerchantOverview(
        total_designs=total_designs,
        active_designs=active_designs,
        total_views=total_views,
        total_try_ons=total_try_ons,
        failed_try_ons=failed_try_ons,
        total_favorites=total_favorites,
        conversion_rate=conversion_rate,
        hot_designs=[
            schemas.MerchantHotDesign(
                id=design.id,
                name=design.name,
                image_url=design.image_url,
                try_on_count=design.try_on_count,
            )
            for design in hot_designs
        ],
        recent_bookings=recent_bookings,
        recent_activity=activities[:8],
    )


@router.get("/today-workbench")
def get_today_workbench(db: Session = Depends(get_db), _operator: models.User = Depends(require_operator)):
    """Get today's action-oriented operations workbench."""
    from app.operations_agent.workbench import build_today_workbench

    return build_today_workbench(db)


@router.get("/config")
def get_config(db: Session = Depends(get_db), _operator: models.User = Depends(require_operator)):
    """Get backend-sourced operations configuration."""
    from app.services.operations_config import get_operations_config

    return get_operations_config(db)


@router.put("/config")
def update_config(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Persist operations configuration without a database schema change."""
    from app.services.operations_config import update_operations_config

    return update_operations_config(db, payload)


@router.get("/trends")
def get_trends(
    days: int = 30,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Get trend analysis for specified period."""
    start_date = datetime.now() - timedelta(days=days)

    # Daily try-on counts
    daily_stats = _business_try_on_query(db).with_entities(
        func.date(models.TryOnRecord.created_at).label("date"),
        func.count(models.TryOnRecord.id).label("try_ons"),
        func.count(func.distinct(models.TryOnRecord.user_id)).label("unique_users")
    ).filter(
        models.TryOnRecord.created_at >= start_date
    ).group_by(
        func.date(models.TryOnRecord.created_at)
    ).order_by("date").all()

    # Style distribution
    recent_records = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= start_date
    ).all()

    style_dist = {}
    for record in recent_records:
        for tag in _design_tags(record.nail_design, "style_tags"):
            style_dist[tag] = style_dist.get(tag, 0) + 1

    # Color distribution
    color_dist = {}
    for record in recent_records:
        for tag in _design_tags(record.nail_design, "color_tags"):
            color_dist[tag] = color_dist.get(tag, 0) + 1

    return {
        "period": f"{days} days",
        "daily_stats": [
            {
                "date": str(stat.date),
                "try_ons": stat.try_ons,
                "unique_users": stat.unique_users
            }
            for stat in daily_stats
        ],
        "style_distribution": style_dist,
        "color_distribution": color_dist
    }


@router.get("/hot-candidates")
def get_hot_candidates(
    limit: int = 20,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Get hot candidate designs (rising trends)."""
    week_ago = datetime.now() - timedelta(days=7)
    two_weeks_ago = datetime.now() - timedelta(days=14)

    # Get designs with recent activity
    designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active"
    ).all()

    candidates = []
    for design in designs:
        # Last 7 days try-ons
        recent_count = _business_try_on_query(db).filter(
            models.TryOnRecord.nail_design_id == design.id,
            models.TryOnRecord.created_at >= week_ago
        ).count()

        # Previous 7 days try-ons
        previous_count = _business_try_on_query(db).filter(
            models.TryOnRecord.nail_design_id == design.id,
            models.TryOnRecord.created_at >= two_weeks_ago,
            models.TryOnRecord.created_at < week_ago
        ).count()

        # Calculate growth rate
        if previous_count > 0:
            growth_rate = (recent_count - previous_count) / previous_count
        else:
            growth_rate = float(recent_count)  # New design

        # Hot candidate criteria
        if recent_count >= 5 or growth_rate >= 0.5:
            reason = []
            if growth_rate >= 1.0:
                reason.append("热度翻倍增长")
            elif growth_rate >= 0.5:
                reason.append("热度快速上升")
            if recent_count >= 20:
                reason.append("本周试戴量高")
            if design.favorite_count >= 10:
                reason.append("收藏转化好")

            candidates.append({
                "design": design_to_response(design),
                "recent_try_ons": recent_count,
                "previous_try_ons": previous_count,
                "growth_rate": growth_rate,
                "reason": "；".join(reason) if reason else "潜力款式"
            })

    # Sort by growth rate
    candidates.sort(key=lambda x: x["growth_rate"], reverse=True)

    return candidates[:limit]


@router.get("/daily-report")
def get_daily_report(db: Session = Depends(get_db), _operator: models.User = Depends(require_operator)):
    """Generate AI daily operations report."""
    today = _current_local_day_start_as_db_naive()
    yesterday = today - timedelta(days=1)

    # Today's stats
    today_try_ons = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= today
    ).count()

    yesterday_try_ons = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= yesterday,
        models.TryOnRecord.created_at < today
    ).count()

    # Trending styles today
    today_records = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= today
    ).all()

    style_counts = {}
    for record in today_records:
        for tag in _design_tags(record.nail_design, "style_tags"):
            style_counts[tag] = style_counts.get(tag, 0) + 1

    top_styles = sorted(style_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Generate summary
    try_on_change = "上升" if today_try_ons > yesterday_try_ons else "下降"
    try_on_diff = abs(today_try_ons - yesterday_try_ons)

    summary = f"今日试戴量 {today_try_ons} 次，较昨日{try_on_change} {try_on_diff} 次。"
    if top_styles:
        summary += f"最热门风格：{', '.join([s[0] for s in top_styles[:3]])}。"

    # Highlights
    highlights = []
    hot_candidates = get_hot_candidates(limit=5, db=db)
    if hot_candidates:
        highlights.append(f"发现 {len(hot_candidates)} 款潜力爆款")

    # Alerts
    alerts = []
    if today_try_ons < yesterday_try_ons * 0.7:
        alerts.append("今日试戴量明显下降，建议检查首页推荐位")

    # Recommendations
    recommendations = []
    if hot_candidates:
        top_candidate = hot_candidates[0]
        recommendations.append({
            "action": "加推热门款式",
            "target": top_candidate["design"]["name"],
            "reason": f"热度增长 {top_candidate['growth_rate']*100:.0f}%"
        })

    # Generate copy for operations
    copy = f"""今日美甲趋势速报

✈️ 今日试戴：{today_try_ons} 次
🔥 热门风格：{', '.join([s[0] for s in top_styles[:3]]) if top_styles else '暂无数据'}

💡 运营建议：
1. 重点推广 {hot_candidates[0]['design']['name'] if hot_candidates else '热门款式'}，当前热度上升
2. 上新 {top_styles[0][0] if top_styles else '流行'} 风格款式，满足用户需求
"""

    return schemas.DailyReport(
        date=today,
        summary=summary,
        highlights=highlights,
        alerts=alerts,
        recommendations=recommendations,
        copy_for_operation=copy
    )


@router.post("/assistant/chat", response_model=schemas.OperationsAssistantChatResponse)
def chat_with_operations_assistant(
    request: schemas.OperationsAssistantChatRequest,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Chat with the read-only operations assistant."""
    from app.operations_agent.runner import OperationsAgentRunner

    runner = OperationsAgentRunner()
    response = runner.chat(
        message=request.message,
        db=db,
        context=request.context,
    )
    return response.model_dump()


@router.get("/assistant/capabilities")
def get_assistant_capabilities(_operator: models.User = Depends(require_operator)):
    """Expose operations Agent runtime capabilities for local acceptance checks."""
    from app.operations_agent.agent_control import get_channel_statuses

    return {
        "version": "agent-v2",
        "features": {
            "structured_evidence": True,
            "safe_action_cards": True,
            "suggestion_center_sync": True,
            "external_message_simulation": True,
            "external_webhook": True,
            "feishu_webhook_delivery": True,
            "scheduled_daily_report": True,
            "weekly_report_intent": True,
            "recommendation_slot_intent": True,
            "agent_runtime_status": True,
        },
        "channels": get_channel_statuses(),
    }


@router.get("/assistant/status")
def get_assistant_status(_operator: models.User = Depends(require_operator)):
    """Expose the Chat-first Agent gateway, schedules, channels, and safety state."""
    from app.operations_agent.agent_control import get_agent_runtime_status

    return get_agent_runtime_status()


@router.post("/assistant/suggestions")
def sync_assistant_suggestions(
    request: schemas.OperationsAssistantSuggestionSyncRequest,
    _operator: models.User = Depends(require_operator),
):
    """Sync Agent action cards to the existing suggestions center."""
    from app.operations_agent.suggestion_store import add_agent_suggestions

    return add_agent_suggestions(
        actions=[action.model_dump() for action in request.actions],
        source_message=request.source_message,
        answer=request.answer,
        evidence=[item.model_dump() for item in request.evidence],
    )


@router.post("/assistant/command")
def apply_assistant_command(
    request: schemas.OperationsAssistantCommandRequest,
    _operator: models.User = Depends(require_operator),
):
    """Apply a safe Agent command, such as syncing action cards to suggestions."""
    from app.operations_agent.agent_control import apply_chat_command

    return apply_chat_command(
        message=request.message,
        assistant_payload=request.assistant_payload,
    )


@router.post("/assistant/external-message")
def handle_assistant_external_message(
    request: schemas.OperationsAssistantExternalMessageRequest,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Receive a message from an external channel such as Feishu, WeChat, or QQ."""
    from app.operations_agent.agent_control import handle_external_message

    return handle_external_message(
        db=db,
        channel=request.channel,
        sender=request.sender,
        message=request.message,
        context=request.context,
    )


@router.post("/assistant/webhook", response_model=schemas.OperationsAssistantExternalReply)
def handle_assistant_webhook(
    request: schemas.OperationsAssistantWebhookRequest,
    db: Session = Depends(get_db),
    x_nailmind_agent_token: str | None = Header(None),
):
    """Receive a generic external Agent webhook from Feishu/WeChat/QQ adapters."""
    settings = get_settings()
    if not settings.OPERATIONS_AGENT_EXTERNAL_ENABLED:
        raise HTTPException(status_code=403, detail="Operations Agent external webhook is disabled")

    expected_token = settings.OPERATIONS_AGENT_EXTERNAL_TOKEN
    provided_token = x_nailmind_agent_token or request.token
    if expected_token and provided_token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid operations Agent webhook token")
    if not expected_token and not settings.DEBUG:
        raise HTTPException(status_code=503, detail="Operations Agent webhook token is not configured")

    text = (request.text or request.message or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Webhook message text is required")

    from app.operations_agent.agent_control import handle_external_message

    return handle_external_message(
        db=db,
        channel=request.channel,
        sender=request.sender,
        message=text,
        context={**(request.context or {}), "source": "external_webhook"},
    )


@router.post("/assistant/webhook/feishu")
def handle_feishu_assistant_webhook(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    x_nailmind_agent_token: str | None = Header(None),
):
    """Receive Feishu event-subscription messages and route text to the operations Agent."""
    if payload.get("type") == "url_verification" and payload.get("challenge"):
        return {"challenge": payload["challenge"]}

    settings = get_settings()
    if not settings.OPERATIONS_AGENT_EXTERNAL_ENABLED:
        raise HTTPException(status_code=403, detail="Operations Agent external webhook is disabled")

    expected_token = settings.OPERATIONS_AGENT_EXTERNAL_TOKEN
    provided_token = x_nailmind_agent_token or payload.get("token")
    if expected_token and provided_token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid operations Agent webhook token")
    if not expected_token and not settings.DEBUG:
        raise HTTPException(status_code=503, detail="Operations Agent webhook token is not configured")

    sender = _extract_feishu_sender(payload)
    text = _extract_feishu_text(payload)
    if not text:
        raise HTTPException(status_code=400, detail="Feishu text message is required")

    from app.operations_agent.agent_control import handle_external_message

    return handle_external_message(
        db=db,
        channel="feishu",
        sender=sender,
        message=text,
        context={"source": "feishu_event", "event_type": (payload.get("header") or {}).get("event_type")},
    )


@router.get("/assistant/schedules")
def get_assistant_schedules(_operator: models.User = Depends(require_operator)):
    """Get external Agent schedule configuration and recent deliveries."""
    from app.operations_agent.agent_control import get_schedules

    return get_schedules()


@router.put("/assistant/schedules/daily-report")
def update_assistant_daily_report_schedule(
    request: schemas.OperationsAssistantScheduleRequest,
    _operator: models.User = Depends(require_operator),
):
    """Configure the demo daily report push task without a schema migration."""
    from app.operations_agent.agent_control import update_daily_report_schedule

    return update_daily_report_schedule(request.model_dump())


@router.post("/assistant/schedules/daily-report/run")
def run_assistant_daily_report_schedule(
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Manually trigger the scheduled daily report push."""
    from app.operations_agent.agent_control import run_daily_report_schedule

    return run_daily_report_schedule(db=db)


@router.post("/booking-intents", response_model=schemas.BookingIntentResponse)
def create_booking_intent(
    intent: schemas.BookingIntentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a booking intent."""
    try_on = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.id == intent.try_on_record_id
    ).first()

    if not try_on:
        raise HTTPException(status_code=404, detail="Try-on record not found")

    if try_on.nail_design_id != intent.nail_design_id:
        raise HTTPException(status_code=400, detail="Try-on record does not match design")
    if try_on.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Try-on record does not belong to current user")
    if try_on.status != "completed" or not try_on.result_image_url:
        raise HTTPException(status_code=400, detail="Try-on result is not ready for booking")
    phone = normalize_phone(intent.phone)

    existing = db.query(models.BookingIntent).filter(
        models.BookingIntent.try_on_record_id == intent.try_on_record_id
    ).first()
    if existing:
        existing.phone = phone
        existing.preferred_date = intent.preferred_date
        existing.notes = intent.notes
        try_on.has_booking_intent = True
        db.commit()
        db.refresh(existing)
        return existing

    # Mark try-on as having booking intent
    try_on.has_booking_intent = True

    # Update design booking count
    design = db.query(models.NailDesign).filter(
        models.NailDesign.id == intent.nail_design_id
    ).first()
    if design:
        design.booking_count += 1

    db_intent = models.BookingIntent(
        user_id=current_user.id,
        try_on_record_id=intent.try_on_record_id,
        nail_design_id=intent.nail_design_id,
        phone=phone,
        preferred_date=intent.preferred_date,
        notes=intent.notes
    )

    db.add(db_intent)
    db.commit()
    db.refresh(db_intent)

    return db_intent


@router.get("/booking-intents")
def list_booking_intents(
    status: str = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """List all booking intents (for operations)."""
    query = db.query(models.BookingIntent)

    if status:
        query = query.filter(models.BookingIntent.status == status)

    intents = query.order_by(
        models.BookingIntent.created_at.desc()
    ).limit(limit).all()

    return [_booking_to_followup_response(db, intent) for intent in intents]


@router.patch("/booking-intents/{booking_id}/status")
def update_booking_intent_status(
    booking_id: int,
    status: str,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Update booking follow-up status for merchant operations."""
    allowed_statuses = {"pending", "contacted", "confirmed", "completed", "cancelled"}
    if status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid booking status")

    booking = db.query(models.BookingIntent).filter(
        models.BookingIntent.id == booking_id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking intent not found")

    _validate_booking_status_transition(booking.status, status)

    booking.status = status
    db.commit()
    db.refresh(booking)
    return _booking_to_followup_response(db, booking)


# ==================== Suggestions (AI Operations Agent) ====================

@router.get("/suggestions")
def get_suggestions(
    status: str = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Get AI-generated operation suggestions."""
    from datetime import datetime, timedelta

    # Generate dynamic suggestions based on current data
    suggestions = []

    # Get current stats
    today = _current_local_day_start_as_db_naive()
    week_ago = today - timedelta(days=7)

    # 1. Hot promotion suggestions
    hot_signal_rows = _business_try_on_query(db).with_entities(
        models.TryOnRecord.nail_design_id.label("design_id"),
        func.count(models.TryOnRecord.id).label("completed_try_ons"),
    ).join(
        models.NailDesign,
        models.NailDesign.id == models.TryOnRecord.nail_design_id,
    ).filter(
        models.NailDesign.status == "active",
        models.NailDesign.is_hot == False,
        models.TryOnRecord.created_at >= week_ago,
    ).group_by(
        models.TryOnRecord.nail_design_id,
    ).having(
        func.count(models.TryOnRecord.id) >= 20
    ).order_by(
        func.count(models.TryOnRecord.id).desc()
    ).limit(3).all()

    hot_signal_counts = {row.design_id: int(row.completed_try_ons or 0) for row in hot_signal_rows}
    hot_candidates = []
    if hot_signal_counts:
        hot_candidates = db.query(models.NailDesign).filter(
            models.NailDesign.id.in_(hot_signal_counts.keys())
        ).all()
        hot_candidates.sort(key=lambda design: hot_signal_counts[design.id], reverse=True)

    for design in hot_candidates:
        completed_try_ons = hot_signal_counts.get(design.id, 0)
        suggestions.append({
            "id": f"hot_{design.id}",
            "type": "hot",
            "priority": "high",
            "title": f"加推热门款式：{design.name}",
            "description": f"该款式近7天试戴量达 {completed_try_ons} 次，收藏转化率 {(design.favorite_count/completed_try_ons*100):.1f}%",
            "target": design.name,
            "reason": f"试戴量增长，用户反馈良好",
            "expected_impact": "预计可提升试戴量 15-20%",
            "status": "pending",
            "created_at": today.isoformat()
        })

    # 2. Cold item suggestions
    cold_designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active",
        models.NailDesign.is_hot == True,
        models.NailDesign.try_on_count < 5
    ).limit(3).all()

    for design in cold_designs:
        suggestions.append({
            "id": f"cold_{design.id}",
            "type": "cold",
            "priority": "medium",
            "title": f"调整低效款式位置：{design.name}",
            "description": f"该款式试戴率持续走低，建议移出热门推荐位",
            "target": design.name,
            "reason": f"连续7天试戴量低于5次",
            "expected_impact": "释放推荐位给更有潜力款式",
            "status": "pending",
            "created_at": today.isoformat()
        })

    # 3. New arrival suggestions
    new_designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active",
        models.NailDesign.created_at >= week_ago
    ).all()
    trending_styles = {
        tag
        for design in new_designs
        for tag in _design_tags(design, "style_tags")
    }

    if trending_styles:
        suggestions.append({
            "id": "new_001",
            "type": "new",
            "priority": "high",
            "title": "上新品类建议",
            "description": "根据近期试戴趋势，建议上架更多流行款式",
            "target": "新品类扩展",
            "reason": f"近7天新增 {len(new_designs)} 个款式，覆盖 {len(trending_styles)} 个风格标签",
            "expected_impact": "满足用户需求，提升整体试戴量",
            "status": "pending",
            "created_at": today.isoformat()
        })

    from app.operations_agent.suggestion_store import list_agent_suggestions

    suggestions = list_agent_suggestions(status=status) + suggestions

    # Filter by status if provided
    if status:
        suggestions = [s for s in suggestions if s["status"] == status]

    return suggestions[:limit]


@router.post("/suggestions/{suggestion_id}/accept")
def accept_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Accept an AI suggestion."""
    from app.operations_agent.suggestion_store import update_agent_suggestion_status

    result = _apply_structured_suggestion(suggestion_id, db)
    agent_suggestion = update_agent_suggestion_status(suggestion_id, "accepted")
    if agent_suggestion:
        return {"id": suggestion_id, "status": "accepted", **result}

    return {"id": suggestion_id, "status": "accepted", **result}


@router.post("/suggestions/{suggestion_id}/reject")
def reject_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Reject an AI suggestion."""
    from app.operations_agent.suggestion_store import update_agent_suggestion_status

    agent_suggestion = update_agent_suggestion_status(suggestion_id, "rejected")
    if agent_suggestion:
        return {"id": suggestion_id, "status": "rejected"}

    return {"id": suggestion_id, "status": "rejected"}


# ==================== Cold Alert (冷门预警) ====================

@router.get("/cold-designs")
def get_cold_designs(
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Get designs that need attention (low performance)."""
    from datetime import datetime, timedelta

    week_ago = datetime.now() - timedelta(days=7)

    # Find designs with low engagement
    cold_designs = []

    designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active"
    ).all()

    for design in designs:
        # Get recent try-ons
        recent_try_ons = _business_try_on_query(db).filter(
            models.TryOnRecord.nail_design_id == design.id,
            models.TryOnRecord.created_at >= week_ago
        ).count()

        # Calculate rates
        try_on_rate = (recent_try_ons / max(design.view_count, 1)) * 100

        # Determine alert type
        alert_type = None
        reason = None
        suggestion = None

        if design.view_count > 50 and try_on_rate < 5:
            alert_type = "高曝光低试戴"
            reason = "曝光量充足但试戴转化低，可能与当前热门风格不符"
            suggestion = "考虑更换推荐位置或调整标签"

        elif recent_try_ons >= 10 and design.favorite_count < 2:
            alert_type = "高试戴低收藏"
            reason = "试戴量大但收藏少，可能效果不如预期"
            suggestion = "检查款式质量，考虑下架或优化"

        elif design.favorite_count >= 5 and design.booking_count == 0:
            alert_type = "高收藏低预约"
            reason = "用户喜欢但未产生预约意愿"
            suggestion = "增加促销引导或优化价格策略"

        if alert_type:
            cold_designs.append({
                "design": {
                    "id": design.id,
                    "name": design.name,
                    "image_url": design.image_url,
                    "view_count": design.view_count,
                    "try_on_count": design.try_on_count,
                    "favorite_count": design.favorite_count,
                    "booking_count": design.booking_count
                },
                "alert_type": alert_type,
                "metrics": {
                    "impressions": design.view_count,
                    "try_on_rate": round(try_on_rate, 1),
                    "favorite_rate": round((design.favorite_count / max(design.try_on_count, 1)) * 100, 1),
                    "booking_rate": round((design.booking_count / max(design.favorite_count, 1)) * 100, 1)
                },
                "reason": reason,
                "suggestion": suggestion
            })

    # Sort by severity (high impressions + low conversion first)
    cold_designs.sort(key=lambda x: x["design"]["view_count"], reverse=True)

    return cold_designs

@router.get("/ai-insights")
def get_ai_insights(db: Session = Depends(get_db), _operator: models.User = Depends(require_operator)):
    """Get AI-generated insights and predictions."""
    from app.ai_agent import AIOperationsAgent
    agent = AIOperationsAgent(db)
    return agent.get_insights_report()


@router.get("/predictions")
def get_predictions(
    days_ahead: int = 7,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Get trend predictions."""
    from app.ai_agent import AIOperationsAgent
    agent = AIOperationsAgent(db)
    return agent.predict_trend(days_ahead)


@router.get("/emerging-styles")
def get_emerging_styles(db: Session = Depends(get_db), _operator: models.User = Depends(require_operator)):
    """Get emerging style trends."""
    from app.ai_agent import AIOperationsAgent
    agent = AIOperationsAgent(db)
    return agent.identify_emerging_styles(14)


@router.get("/inventory-recommendations")
def get_inventory_recs(db: Session = Depends(get_db), _operator: models.User = Depends(require_operator)):
    """Get inventory recommendations."""
    from app.ai_agent import AIOperationsAgent
    agent = AIOperationsAgent(db)
    return agent.generate_inventory_recommendations()


@router.get("/anomalies")
def get_anomalies(db: Session = Depends(get_db), _operator: models.User = Depends(require_operator)):
    """Get data anomalies."""
    from app.ai_agent import AIOperationsAgent
    agent = AIOperationsAgent(db)
    return agent.detect_anomalies(7)


@router.get("/action-plan")
def get_action_plan(db: Session = Depends(get_db), _operator: models.User = Depends(require_operator)):
    """Get AI-generated action plan."""
    from app.ai_agent import AIOperationsAgent
    agent = AIOperationsAgent(db)
    return agent.generate_action_plan()




# ==================== Style & Scene Analysis ====================

@router.get("/style-analysis")
def get_style_analysis(
    days: int = 30,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Detailed style trend analysis."""
    from datetime import datetime, timedelta

    start_date = datetime.now() - timedelta(days=days)

    # Get all try-ons in period
    try_ons = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= start_date
    ).all()

    # Analyze by style
    style_stats = {}
    for try_on in try_ons:
        style_tags = _design_tags(try_on.nail_design, "style_tags")
        if not style_tags:
            continue

        for style in style_tags:
            if style not in style_stats:
                style_stats[style] = {
                    "try_ons": 0,
                    "favorites": 0,
                    "bookings": 0,
                    "unique_users": set()
                }
            style_stats[style]["try_ons"] += 1
            style_stats[style]["unique_users"].add(try_on.user_id)
            if try_on.is_favorite:
                style_stats[style]["favorites"] += 1

    # Calculate conversion rates
    style_analysis = []
    for style, stats in style_stats.items():
        try_ons = stats["try_ons"]
        favorites = stats["favorites"]
        unique_users = len(stats["unique_users"])

        analysis = {
            "style": style,
            "try_ons": try_ons,
            "unique_users": unique_users,
            "favorites": favorites,
            "favorite_rate": round(favorites / try_ons * 100, 1) if try_ons > 0 else 0,
            "popularity_score": round(try_ons * 0.5 + favorites * 2 + unique_users * 0.3, 1)
        }
        style_analysis.append(analysis)

    # Sort by popularity score
    style_analysis.sort(key=lambda x: x["popularity_score"], reverse=True)

    # Identify trends
    top_styles = style_analysis[:5] if len(style_analysis) >= 5 else style_analysis
    rising_styles = [s for s in style_analysis if s["favorite_rate"] > 30][:3]

    return {
        "period_days": days,
        "total_styles": len(style_analysis),
        "top_styles": top_styles,
        "rising_styles": rising_styles,
        "all_styles": style_analysis
    }


@router.get("/scene-analysis")
def get_scene_analysis(
    days: int = 30,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Detailed scene/occasion trend analysis."""
    from datetime import datetime, timedelta

    start_date = datetime.now() - timedelta(days=days)

    # Get all try-ons in period
    try_ons = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= start_date
    ).all()

    # Analyze by scene
    scene_stats = {}
    for try_on in try_ons:
        design = try_on.nail_design
        scene_tags = _design_tags(design, "scene_tags")
        style_tags = _design_tags(design, "style_tags")
        if not scene_tags:
            continue

        for scene in scene_tags:
            if scene not in scene_stats:
                scene_stats[scene] = {
                    "try_ons": 0,
                    "favorites": 0,
                    "bookings": 0,
                    "unique_users": set(),
                    "related_styles": {}
                }
            scene_stats[scene]["try_ons"] += 1
            scene_stats[scene]["unique_users"].add(try_on.user_id)
            if try_on.is_favorite:
                scene_stats[scene]["favorites"] += 1
            if try_on.has_booking_intent:
                scene_stats[scene]["bookings"] += 1

            # Track related styles
            for style in style_tags:
                scene_stats[scene]["related_styles"][style] = \
                    scene_stats[scene]["related_styles"].get(style, 0) + 1

    # Calculate metrics
    scene_analysis = []
    for scene, stats in scene_stats.items():
        try_ons = stats["try_ons"]
        favorites = stats["favorites"]
        bookings = stats["bookings"]
        unique_users = len(stats["unique_users"])

        # Get top styles for this scene
        top_styles = sorted(
            stats["related_styles"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        analysis = {
            "scene": scene,
            "try_ons": try_ons,
            "unique_users": unique_users,
            "favorites": favorites,
            "bookings": bookings,
            "favorite_rate": round(favorites / try_ons * 100, 1) if try_ons > 0 else 0,
            "booking_rate": round(bookings / max(favorites, 1) * 100, 1),
            "top_styles": [s[0] for s in top_styles],
            "demand_score": round(try_ons + favorites * 2 + bookings * 5, 1)
        }
        scene_analysis.append(analysis)

    # Sort by demand score
    scene_analysis.sort(key=lambda x: x["demand_score"], reverse=True)

    return {
        "period_days": days,
        "total_scenes": len(scene_analysis),
        "top_scenes": scene_analysis[:5],
        "high_conversion_scenes": sorted(
            scene_analysis,
            key=lambda x: x["booking_rate"],
            reverse=True
        )[:3],
        "all_scenes": scene_analysis
    }


@router.get("/color-analysis")
def get_color_analysis(
    days: int = 30,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Color trend analysis."""
    from datetime import datetime, timedelta

    start_date = datetime.now() - timedelta(days=days)

    try_ons = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= start_date
    ).all()

    color_stats = {}
    for try_on in try_ons:
        color_tags = _design_tags(try_on.nail_design, "color_tags")
        if not color_tags:
            continue

        for color in color_tags:
            if color not in color_stats:
                color_stats[color] = {
                    "try_ons": 0,
                    "favorites": 0,
                    "unique_users": set()
                }
            color_stats[color]["try_ons"] += 1
            color_stats[color]["unique_users"].add(try_on.user_id)
            if try_on.is_favorite:
                color_stats[color]["favorites"] += 1

    color_analysis = []
    for color, stats in color_stats.items():
        try_ons = stats["try_ons"]
        favorites = stats["favorites"]
        unique_users = len(stats["unique_users"])

        analysis = {
            "color": color,
            "try_ons": try_ons,
            "unique_users": unique_users,
            "favorites": favorites,
            "favorite_rate": round(favorites / try_ons * 100, 1) if try_ons > 0 else 0,
            "trend_score": round(try_ons * 0.3 + favorites * 1.5 + unique_users * 0.2, 1)
        }
        color_analysis.append(analysis)

    color_analysis.sort(key=lambda x: x["trend_score"], reverse=True)

    return {
        "period_days": days,
        "top_colors": color_analysis[:8],
        "rising_colors": [c for c in color_analysis if c["favorite_rate"] > 25][:3]
    }


@router.get("/funnel")
def get_funnel(
    days: int = 30,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Get conversion funnel data for specified period."""
    start_date = datetime.now() - timedelta(days=days)

    # Total views (cumulative across all designs)
    total_views = db.query(func.sum(models.NailDesign.view_count)).scalar() or 0

    # Period-specific metrics
    total_try_ons = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= start_date
    ).count()

    total_favorites = db.query(models.Favorite).filter(
        models.Favorite.created_at >= start_date
    ).count()

    total_bookings = db.query(models.BookingIntent).filter(
        models.BookingIntent.created_at >= start_date
    ).count()

    # Conversion rates
    try_on_rate = round(total_try_ons / total_views * 100, 2) if total_views > 0 else 0
    favorite_rate = round(total_favorites / total_try_ons * 100, 2) if total_try_ons > 0 else 0
    booking_rate = round(total_bookings / total_favorites * 100, 2) if total_favorites > 0 else 0
    overall_conversion = round(total_bookings / total_views * 100, 2) if total_views > 0 else 0

    return {
        "period_days": days,
        "stages": [
            {"name": "浏览", "count": total_views, "conversion_rate": 100.0},
            {"name": "试戴", "count": total_try_ons, "conversion_rate": try_on_rate},
            {"name": "收藏", "count": total_favorites, "conversion_rate": favorite_rate},
            {"name": "预约", "count": total_bookings, "conversion_rate": booking_rate}
        ],
        "overall_conversion": overall_conversion
    }


@router.get("/daily-report/historical")
def get_historical_report(
    date_str: str,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Get daily report for a specific historical date (YYYY-MM-DD)."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    target_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    target_end = target_start + timedelta(days=1)

    # Try to find pre-computed trend daily record
    trend_record = db.query(models.TrendDaily).filter(
        models.TrendDaily.date >= target_start,
        models.TrendDaily.date < target_end
    ).first()

    if trend_record and trend_record.ai_summary:
        return schemas.DailyReport(
            date=target_start,
            summary=trend_record.ai_summary,
            highlights=trend_record.hot_designs or [],
            alerts=[],
            recommendations=trend_record.ai_recommendations or [],
            copy_for_operation=trend_record.ai_summary
        )

    # Fallback: compute from raw data
    day_try_ons = _business_try_on_query(db).filter(
        models.TryOnRecord.created_at >= target_start,
        models.TryOnRecord.created_at < target_end
    ).count()

    day_favorites = db.query(models.Favorite).filter(
        models.Favorite.created_at >= target_start,
        models.Favorite.created_at < target_end
    ).count()

    day_bookings = db.query(models.BookingIntent).filter(
        models.BookingIntent.created_at >= target_start,
        models.BookingIntent.created_at < target_end
    ).count()

    summary = f"{date_str} 试戴量 {day_try_ons} 次，收藏 {day_favorites} 次，预约 {day_bookings} 次。"

    return schemas.DailyReport(
        date=target_start,
        summary=summary,
        highlights=[],
        alerts=[],
        recommendations=[],
        copy_for_operation=summary
    )
