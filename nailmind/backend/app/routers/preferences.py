"""User preference profile routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from typing import List, Dict
from collections import Counter
import json

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.design_visual_tags import design_to_effective_tags, design_to_response

router = APIRouter()

COMPLETED_TRY_ON_STATUSES = {"completed"}


def _effective_design(design: models.NailDesign) -> dict:
    return design_to_effective_tags(design)


def calculate_user_preferences(user_id: int, db: Session) -> models.UserPreference:
    """Calculate user preferences based on their behavior."""
    # Get or create preference record
    with db.no_autoflush:
        pref = db.query(models.UserPreference).filter(
            models.UserPreference.user_id == user_id
        ).first()

    if not pref:
        pref = models.UserPreference(user_id=user_id)
        db.add(pref)

    # Get user's try-on records with designs
    try_ons = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.user_id == user_id,
        models.TryOnRecord.status.in_(COMPLETED_TRY_ON_STATUSES),
    ).all()

    # Get user's favorites
    favorites = db.query(models.Favorite).filter(
        models.Favorite.user_id == user_id
    ).all()

    # Get favorite design IDs
    favorite_design_ids = {f.nail_design_id for f in favorites}

    # Collect style/color/scene preferences
    style_counter = Counter()
    color_counter = Counter()
    scene_counter = Counter()
    length_counter = Counter()
    shape_counter = Counter()

    for try_on in try_ons:
        design = try_on.nail_design
        if design:
            effective = _effective_design(design)
            # Weight favorites more heavily
            weight = 2.0 if try_on.nail_design_id in favorite_design_ids else 1.0
            if try_on.is_candidate:
                weight += 1.0  # Candidates also get extra weight
            if try_on.has_booking_intent:
                weight += 2.0

            for style in effective["style_tags"]:
                style_counter[style] += weight
            for color in effective["color_tags"]:
                color_counter[color] += weight
            for scene in effective["scene_tags"]:
                scene_counter[scene] += weight
            if effective["length"]:
                length_counter[effective["length"]] += weight
            if effective["shape"]:
                shape_counter[effective["shape"]] += weight

    # Add favorites (even if not tried on)
    for fav in favorites:
        design = db.query(models.NailDesign).filter(
            models.NailDesign.id == fav.nail_design_id
        ).first()
        if design:
            effective = _effective_design(design)
            for style in effective["style_tags"]:
                style_counter[style] += 2.0
            for color in effective["color_tags"]:
                color_counter[color] += 2.0

    # Normalize to scores (0-1)
    def normalize_counter(counter: Counter) -> List[Dict]:
        if not counter:
            return []
        total = sum(counter.values())
        max_count = max(counter.values())
        return [
            {"name": item, "score": round(count / max_count, 2), "count": int(count)}
            for item, count in counter.most_common(5)
        ]

    pref.preferred_styles = normalize_counter(style_counter)
    pref.preferred_colors = normalize_counter(color_counter)
    pref.preferred_scenes = normalize_counter(scene_counter)

    # Most common length/shape
    if length_counter:
        pref.preferred_length = length_counter.most_common(1)[0][0]
    if shape_counter:
        pref.preferred_shape = shape_counter.most_common(1)[0][0]

    # Update stats
    pref.total_try_ons = len(try_ons)
    pref.total_favorites = len(favorites)
    pref.total_candidates = sum(1 for t in try_ons if t.is_candidate)
    pref.total_bookings = db.query(models.BookingIntent).filter(
        models.BookingIntent.user_id == user_id
    ).count()

    pref.last_calculated_at = func.now()
    try:
        db.commit()
        db.refresh(pref)
    except IntegrityError:
        db.rollback()
        pref = db.query(models.UserPreference).filter(
            models.UserPreference.user_id == user_id
        ).first()
        if not pref:
            raise

    return pref


@router.get("/", response_model=schemas.UserPreferenceResponse)
def get_user_preferences(
    user_id: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get user preference profile."""
    target_user_id = user_id or current_user.id
    if target_user_id != current_user.id and current_user.user_type not in {"merchant", "admin"}:
        raise HTTPException(status_code=403, detail="Cannot read another user's preferences")
    pref = calculate_user_preferences(target_user_id, db)
    return pref


@router.get("/me", response_model=schemas.UserPreferenceResponse)
def get_my_preferences(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get current user's preference profile."""
    return calculate_user_preferences(current_user.id, db)


@router.post("/calculate")
def recalculate_preferences(
    user_id: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Recalculate user preferences."""
    target_user_id = user_id or current_user.id
    if target_user_id != current_user.id and current_user.user_type not in {"merchant", "admin"}:
        raise HTTPException(status_code=403, detail="Cannot recalculate another user's preferences")
    pref = calculate_user_preferences(target_user_id, db)
    return {"status": "success", "last_calculated_at": pref.last_calculated_at}


@router.get("/recommendations")
def get_personalized_recommendations(
    user_id: int = None,
    limit: int = 6,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get personalized recommendations based on preferences."""
    target_user_id = user_id or current_user.id
    if target_user_id != current_user.id and current_user.user_type not in {"merchant", "admin"}:
        raise HTTPException(status_code=403, detail="Cannot read another user's recommendations")
    pref = calculate_user_preferences(target_user_id, db)

    # Get preferred styles/colors
    top_styles = [s["name"] for s in pref.preferred_styles[:3]]
    top_colors = [c["name"] for c in pref.preferred_colors[:3]]

    tried_design_ids = {
        record.nail_design_id
        for record in db.query(models.TryOnRecord.nail_design_id).filter(
            models.TryOnRecord.user_id == target_user_id,
            models.TryOnRecord.status.in_(COMPLETED_TRY_ON_STATUSES),
        ).all()
    }

    # Find matching designs
    designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active",
        ~models.NailDesign.id.in_(tried_design_ids) if tried_design_ids else True,
    ).all()

    # Score each design
    scored_designs = []
    for design in designs:
        effective = _effective_design(design)
        score = 0
        reasons = []

        for style in effective["style_tags"]:
            for pref_style in pref.preferred_styles:
                if pref_style["name"] == style:
                    score += pref_style["score"] * 10
                    reasons.append(f"你喜欢的{style}风格")

        for color in effective["color_tags"]:
            for pref_color in pref.preferred_colors:
                if pref_color["name"] == color:
                    score += pref_color["score"] * 8
                    reasons.append(f"适合你偏好的{color}")

        for scene in effective["scene_tags"]:
            for pref_scene in pref.preferred_scenes:
                if pref_scene["name"] == scene:
                    score += pref_scene["score"] * 5

        if score > 0:
            scored_designs.append({
                "design": design,
                "score": score,
                "reasons": list(set(reasons))[:2]  # Top 2 unique reasons
            })

    # Sort by score
    scored_designs.sort(key=lambda x: x["score"], reverse=True)

    return {
        "based_on": {
            "styles": pref.preferred_styles[:3],
            "colors": pref.preferred_colors[:3]
        },
        "recommendations": [
            {
                "design": design_to_response(item["design"]),
                "match_score": round(item["score"], 1),
                "reasons": item["reasons"]
            }
            for item in scored_designs[:limit]
        ]
    }


@router.get("/me/recommendations")
def get_my_personalized_recommendations(
    limit: int = 6,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get personalized recommendations for the authenticated user."""
    return get_personalized_recommendations(
        user_id=current_user.id,
        limit=limit,
        db=db,
        current_user=current_user,
    )


@router.put("/skin-tone")
def update_skin_tone(
    skin_tone: str,
    skin_undertone: str = None,
    user_id: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update user's skin tone information."""
    target_user_id = user_id or current_user.id
    if target_user_id != current_user.id and current_user.user_type not in {"merchant", "admin"}:
        raise HTTPException(status_code=403, detail="Cannot update another user's preferences")
    pref = db.query(models.UserPreference).filter(
        models.UserPreference.user_id == target_user_id
    ).first()

    if not pref:
        pref = models.UserPreference(user_id=target_user_id)
        db.add(pref)

    pref.skin_tone = skin_tone
    if skin_undertone:
        pref.skin_undertone = skin_undertone

    db.commit()
    return {"status": "success", "skin_tone": skin_tone, "skin_undertone": skin_undertone}


@router.put("/me/skin-tone")
def update_my_skin_tone(
    skin_tone: str,
    skin_undertone: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update current user's skin tone information."""
    return update_skin_tone(
        skin_tone=skin_tone,
        skin_undertone=skin_undertone,
        user_id=current_user.id,
        db=db,
        current_user=current_user,
    )
