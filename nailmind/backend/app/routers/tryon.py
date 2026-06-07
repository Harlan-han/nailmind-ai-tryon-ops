"""Try-on generation routes."""
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime, timezone
import httpx

from app.database import get_db
from app.database import SessionLocal
from app.config import get_settings
from app import models, schemas
from app.auth import get_current_user
from app.services.design_visual_tags import design_to_response

router = APIRouter()
settings = get_settings()

COMPLETED_TRY_ON_STATUSES = ("completed",)
VALID_TRY_ON_RESULT_STATUSES = {"completed", "failed"}
TERMINAL_TRY_ON_RESULT_STATUSES = VALID_TRY_ON_RESULT_STATUSES


def utc_now_naive() -> datetime:
    """Return a UTC timestamp that matches SQLite CURRENT_TIMESTAMP semantics."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def try_on_to_response(try_on: models.TryOnRecord) -> dict:
    """Serialize try-on records with the visual tag overlay on nested designs."""
    return {
        "id": try_on.id,
        "user_id": try_on.user_id,
        "hand_photo_id": try_on.hand_photo_id,
        "nail_design_id": try_on.nail_design_id,
        "result_image_url": try_on.result_image_url,
        "status": try_on.status,
        "error_message": try_on.error_message,
        "is_favorite": try_on.is_favorite,
        "is_candidate": try_on.is_candidate,
        "has_booking_intent": try_on.has_booking_intent,
        "created_at": try_on.created_at,
        "completed_at": try_on.completed_at,
        "nail_design": design_to_response(try_on.nail_design) if try_on.nail_design else None,
    }


def ensure_try_on_access(try_on: models.TryOnRecord, current_user: models.User) -> None:
    """Allow users to read their own try-on records while operators can inspect support cases."""
    if try_on.user_id != current_user.id and current_user.user_type not in {"merchant", "admin"}:
        raise HTTPException(status_code=403, detail="Cannot read another user's try-on record")


def ensure_try_on_owner_for_intent(try_on: models.TryOnRecord, current_user: models.User) -> None:
    """Only the owner can create user intent signals such as favorites and candidates."""
    if try_on.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot update another user's try-on record")


def ensure_try_on_ready_for_intent(try_on: models.TryOnRecord) -> None:
    """User intent should only be attached to visible, completed try-on results."""
    if try_on.status not in COMPLETED_TRY_ON_STATUSES or not try_on.result_image_url:
        raise HTTPException(status_code=400, detail="Try-on result is not ready for user intent")


def ensure_active_design(design: models.NailDesign | None) -> models.NailDesign:
    if not design or design.status != "active":
        raise HTTPException(status_code=404, detail="Design not found")
    return design


def build_try_on_progress(try_on: models.TryOnRecord) -> dict:
    """Build a stable task progress view without adding database columns."""
    now = utc_now_naive()
    updated_at = try_on.completed_at or now
    started_at = try_on.created_at or now
    if started_at.tzinfo is not None:
        started_at = started_at.astimezone(timezone.utc).replace(tzinfo=None)
    elapsed_until = try_on.completed_at or now
    if elapsed_until.tzinfo is not None:
        elapsed_until = elapsed_until.astimezone(timezone.utc).replace(tzinfo=None)
    elapsed_seconds = max(0, int((elapsed_until - started_at).total_seconds()))

    if try_on.status == "completed" and try_on.result_image_url:
        return {
            "try_on_id": try_on.id,
            "status": try_on.status,
            "progress": 100,
            "phase": "completed",
            "message": "试戴效果已生成，点击即可查看结果",
            "result_image_url": try_on.result_image_url,
            "error_message": try_on.error_message,
            "started_at": started_at,
            "elapsed_seconds": elapsed_seconds,
            "updated_at": updated_at,
        }

    if try_on.status == "fallback_completed":
        return {
            "try_on_id": try_on.id,
            "status": "failed",
            "progress": 100,
            "phase": "failed",
            "message": "AI 试戴生成失败，请重新发起试戴",
            "result_image_url": None,
            "error_message": try_on.error_message or "Local fallback result is no longer used",
            "started_at": started_at,
            "elapsed_seconds": elapsed_seconds,
            "updated_at": updated_at,
        }

    if try_on.status == "failed":
        return {
            "try_on_id": try_on.id,
            "status": try_on.status,
            "progress": 100,
            "phase": "failed",
            "message": "本次试戴生成失败，可以重新上传后再试一次",
            "result_image_url": try_on.result_image_url,
            "error_message": try_on.error_message,
            "started_at": started_at,
            "elapsed_seconds": elapsed_seconds,
            "updated_at": updated_at,
        }

    if elapsed_seconds < 8:
        progress = 12 + int(elapsed_seconds * 1.6)
        phase = "queued"
        message = "任务已提交，正在进入 AI 生成队列"
    elif elapsed_seconds < 25:
        progress = 25 + int((elapsed_seconds - 8) * 1.6)
        phase = "analyzing"
        message = "AI 正在分析手部照片与款式参考"
    elif elapsed_seconds < 55:
        progress = 52 + int((elapsed_seconds - 25) * 0.9)
        phase = "generating"
        message = "正在生成试戴效果，复杂款式会稍慢一些"
    elif elapsed_seconds < 110:
        progress = 79 + int((elapsed_seconds - 55) * 0.25)
        phase = "finalizing"
        message = "正在做细节融合和结果保存"
    else:
        progress = 96 + min(2, int((elapsed_seconds - 110) / 45))
        phase = "waiting"
        message = "生成时间比平时更长，任务仍在后台继续"

    return {
        "try_on_id": try_on.id,
        "status": try_on.status or "processing",
        "progress": min(progress, 98),
        "phase": phase,
        "message": message,
        "result_image_url": try_on.result_image_url,
        "error_message": try_on.error_message,
        "started_at": started_at,
        "elapsed_seconds": elapsed_seconds,
        "updated_at": updated_at,
    }


async def dispatch_ai_generation(hand_photo_url: str, design_image_url: str, try_on_id: int):
    """Dispatch try-on generation to the AI service without blocking the request."""
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            response = await client.post(
                f"{settings.AI_SERVICE_URL}/generate",
                json={
                    "hand_photo_url": hand_photo_url,
                    "design_image_url": design_image_url,
                    "try_on_id": try_on_id,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            print(f"Failed to dispatch AI generation for try_on_id={try_on_id}: {exc}")
            mark_try_on_dispatch_failed(try_on_id, str(exc))
            return None


def mark_try_on_dispatch_failed(try_on_id: int, error_message: str) -> None:
    """Make AI dispatch failures visible to users instead of leaving tasks stuck."""
    db = SessionLocal()
    try:
        try_on = db.query(models.TryOnRecord).filter(
            models.TryOnRecord.id == try_on_id,
            models.TryOnRecord.status.in_(["pending", "processing"]),
        ).first()
        if not try_on:
            return
        try_on.status = "failed"
        try_on.error_message = error_message[:1000]
        try_on.completed_at = utc_now_naive()
        db.commit()
    finally:
        db.close()


@router.post("/", response_model=schemas.TryOnResponse)
async def create_try_on(
    request: schemas.TryOnRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new try-on request."""
    hand_photo = db.query(models.HandPhoto).filter(
        models.HandPhoto.id == request.hand_photo_id
    ).first()
    if not hand_photo:
        raise HTTPException(status_code=404, detail="Hand photo not found")
    if hand_photo.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Hand photo does not belong to current user")
    if hand_photo.status != "active":
        raise HTTPException(status_code=404, detail="Hand photo not found")

    design = db.query(models.NailDesign).filter(
        models.NailDesign.id == request.nail_design_id
    ).first()
    design = ensure_active_design(design)

    existing_try_on = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.hand_photo_id == request.hand_photo_id,
        models.TryOnRecord.nail_design_id == request.nail_design_id,
        models.TryOnRecord.status.in_(["pending", "processing"]),
    ).order_by(models.TryOnRecord.created_at.desc()).first()
    if existing_try_on:
        return existing_try_on

    try_on = models.TryOnRecord(
        user_id=hand_photo.user_id,
        hand_photo_id=request.hand_photo_id,
        nail_design_id=request.nail_design_id,
        status="processing"
    )
    db.add(try_on)
    db.commit()
    db.refresh(try_on)

    background_tasks.add_task(
        dispatch_ai_generation,
        hand_photo.image_url,
        design.image_url,
        try_on.id,
    )

    return try_on


@router.get("/me/records", response_model=List[schemas.TryOnResponse])
def get_my_try_ons(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get try-on records for the authenticated user."""
    try_ons = db.query(models.TryOnRecord).options(
        joinedload(models.TryOnRecord.nail_design)
    ).filter(
        models.TryOnRecord.user_id == current_user.id
    ).order_by(models.TryOnRecord.created_at.desc()).limit(limit).all()

    return [try_on_to_response(try_on) for try_on in try_ons]


@router.get("/me/candidates", response_model=List[schemas.TryOnResponse])
def get_my_candidate_try_ons(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all completed candidate try-ons for the authenticated user."""
    try_ons = db.query(models.TryOnRecord).options(
        joinedload(models.TryOnRecord.nail_design)
    ).filter(
        models.TryOnRecord.user_id == current_user.id,
        models.TryOnRecord.is_candidate == True,
        models.TryOnRecord.status.in_(COMPLETED_TRY_ON_STATUSES),
        models.TryOnRecord.result_image_url.isnot(None),
    ).order_by(models.TryOnRecord.created_at.desc()).limit(limit).all()

    return [try_on_to_response(try_on) for try_on in try_ons]


@router.get("/{try_on_id}", response_model=schemas.TryOnResponse)
def get_try_on(
    try_on_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get try-on record by ID."""
    try_on = db.query(models.TryOnRecord).options(
        joinedload(models.TryOnRecord.nail_design)
    ).filter(
        models.TryOnRecord.id == try_on_id
    ).first()

    if not try_on:
        raise HTTPException(status_code=404, detail="Try-on record not found")
    ensure_try_on_access(try_on, current_user)

    return try_on_to_response(try_on)


@router.get("/{try_on_id}/progress", response_model=schemas.TryOnProgressResponse)
def get_try_on_progress(
    try_on_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the user-facing generation progress for a try-on task."""
    try_on = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.id == try_on_id
    ).first()

    if not try_on:
        raise HTTPException(status_code=404, detail="Try-on record not found")
    ensure_try_on_access(try_on, current_user)

    return build_try_on_progress(try_on)


@router.get("/user/{user_id}", response_model=List[schemas.TryOnResponse])
def get_user_try_ons(
    user_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all try-on records for a user."""
    if user_id != current_user.id and current_user.user_type not in {"merchant", "admin"}:
        raise HTTPException(status_code=403, detail="Cannot read another user's try-on records")
    try_ons = db.query(models.TryOnRecord).options(
        joinedload(models.TryOnRecord.nail_design)
    ).filter(
        models.TryOnRecord.user_id == user_id
    ).order_by(models.TryOnRecord.created_at.desc()).limit(limit).all()

    return [try_on_to_response(try_on) for try_on in try_ons]


@router.post("/webhook/result")
async def receive_try_on_result(
    result: schemas.TryOnResultWebhook,
    db: Session = Depends(get_db),
    x_nailmind_webhook_secret: str = Header(default=""),
):
    """Receive try-on result from AI service webhook."""
    if not settings.DEBUG and not settings.AI_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="AI webhook secret is not configured")
    if settings.AI_WEBHOOK_SECRET and x_nailmind_webhook_secret != settings.AI_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    if result.status not in VALID_TRY_ON_RESULT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid try-on result status")
    if result.status in COMPLETED_TRY_ON_STATUSES and not result.result_image_url:
        raise HTTPException(status_code=400, detail="Completed try-on result requires result_image_url")

    try_on = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.id == result.try_on_id
    ).first()

    if not try_on:
        raise HTTPException(status_code=404, detail="Try-on record not found")

    was_completed = try_on.status in COMPLETED_TRY_ON_STATUSES
    if was_completed and result.status not in COMPLETED_TRY_ON_STATUSES:
        return {"status": "success", "ignored": True}
    if try_on.status == "completed" and result.status == "completed" and try_on.result_image_url:
        return {"status": "success", "ignored": True}

    try_on.result_image_url = result.result_image_url
    try_on.status = result.status
    try_on.error_message = result.error_message
    if result.status in TERMINAL_TRY_ON_RESULT_STATUSES:
        from sqlalchemy.sql import func
        try_on.completed_at = func.now()
    if result.status in COMPLETED_TRY_ON_STATUSES:
        if not was_completed and try_on.nail_design:
            try_on.nail_design.try_on_count += 1

    db.commit()
    return {"status": "success"}


@router.post("/{try_on_id}/favorite")
def toggle_favorite(
    try_on_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Toggle favorite status for a try-on."""
    try_on = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.id == try_on_id
    ).first()

    if not try_on:
        raise HTTPException(status_code=404, detail="Try-on record not found")
    ensure_try_on_owner_for_intent(try_on, current_user)
    ensure_try_on_ready_for_intent(try_on)

    design = db.query(models.NailDesign).filter(
        models.NailDesign.id == try_on.nail_design_id
    ).first()
    design = ensure_active_design(design)

    if try_on.is_favorite:
        favorite = db.query(models.Favorite).filter(
            models.Favorite.user_id == current_user.id,
            models.Favorite.nail_design_id == try_on.nail_design_id,
        ).first()
        if favorite:
            db.delete(favorite)
        try_on.is_favorite = False
        design.favorite_count = max(0, design.favorite_count - 1)
    else:
        favorite = db.query(models.Favorite).filter(
            models.Favorite.user_id == current_user.id,
            models.Favorite.nail_design_id == try_on.nail_design_id,
        ).first()
        if not favorite:
            db.add(models.Favorite(
                user_id=current_user.id,
                nail_design_id=try_on.nail_design_id,
                try_on_record_id=try_on.id,
            ))
            design.favorite_count += 1
        elif favorite.try_on_record_id is None:
            favorite.try_on_record_id = try_on.id
        try_on.is_favorite = True

    db.commit()

    return {"is_favorite": try_on.is_favorite}


@router.post("/{try_on_id}/candidate")
def toggle_candidate(
    try_on_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Toggle candidate status for a try-on."""
    try_on = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.id == try_on_id
    ).first()

    if not try_on:
        raise HTTPException(status_code=404, detail="Try-on record not found")
    ensure_try_on_owner_for_intent(try_on, current_user)
    ensure_try_on_ready_for_intent(try_on)
    design = db.query(models.NailDesign).filter(
        models.NailDesign.id == try_on.nail_design_id
    ).first()
    ensure_active_design(design)

    try_on.is_candidate = not try_on.is_candidate
    db.commit()

    return {"is_candidate": try_on.is_candidate}
