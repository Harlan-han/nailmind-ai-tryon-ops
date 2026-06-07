"""Recommendation engine routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.design_visual_tags import (
    deduplicate_designs_by_image,
    design_to_effective_tags,
    design_to_response,
    filter_servable_designs,
)
from app.routers.tryon import ensure_try_on_access
from app.routers.designs import order_designs_by_completed_try_ons

router = APIRouter()


def _effective(design: models.NailDesign) -> dict:
    return design_to_effective_tags(design)


def get_similar_designs(design: models.NailDesign, db: Session, limit: int = 4):
    """Find similar designs based on tags with detailed reasoning."""
    query = db.query(models.NailDesign).filter(
        models.NailDesign.id != design.id,
        models.NailDesign.status == "active"
    )

    candidates = filter_servable_designs(query.all())
    candidates = deduplicate_designs_by_image(sorted(candidates, key=lambda design: int(design.id or 0)))
    scored = []
    design_tags = _effective(design)

    for candidate in candidates:
        reasons = []
        score = 0
        candidate_tags = _effective(candidate)

        # Style tag overlap
        if design_tags["style_tags"] and candidate_tags["style_tags"]:
            style_overlap = set(design_tags["style_tags"]) & set(candidate_tags["style_tags"])
            if style_overlap:
                score += len(style_overlap) * 3
                reasons.append(f"同样是{list(style_overlap)[0]}风格")

        # Color tag overlap
        if design_tags["color_tags"] and candidate_tags["color_tags"]:
            color_overlap = set(design_tags["color_tags"]) & set(candidate_tags["color_tags"])
            if color_overlap:
                score += len(color_overlap) * 2
                colors = list(color_overlap)
                if len(colors) == 1:
                    reasons.append(f"{colors[0]}系配色")
                else:
                    reasons.append(f"相似的{colors[0]}、{colors[1]}配色")

        # Scene tag overlap
        if design_tags["scene_tags"] and candidate_tags["scene_tags"]:
            scene_overlap = set(design_tags["scene_tags"]) & set(candidate_tags["scene_tags"])
            if scene_overlap:
                score += len(scene_overlap) * 2
                reasons.append(f"适合{list(scene_overlap)[0]}")

        # Same length/shape
        if design_tags["length"] and candidate_tags["length"] and design_tags["length"] == candidate_tags["length"]:
            score += 1
            if not reasons:
                reasons.append(f"{candidate_tags['length']}甲长度")
        if design_tags["shape"] and candidate_tags["shape"] and design_tags["shape"] == candidate_tags["shape"]:
            score += 1
            if not reasons:
                reasons.append(f"{candidate_tags['shape']}甲型")

        if score > 0:
            scored.append((candidate, score, reasons))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def get_better_for_you(try_on: models.TryOnRecord, db: Session, limit: int = 4):
    """Find designs that might be better suited with detailed reasoning."""
    design = try_on.nail_design
    user = try_on.user

    query = db.query(models.NailDesign).filter(
        models.NailDesign.id != design.id,
        models.NailDesign.status == "active"
    )

    candidates = filter_servable_designs(query.all())
    candidates = deduplicate_designs_by_image(sorted(candidates, key=lambda design: int(design.id or 0)))
    recommendations = []
    design_tags = _effective(design)

    for candidate in candidates:
        reasons = []
        match_score = 0
        candidate_tags = _effective(candidate)

        # Color-based recommendations with skin tone consideration
        if design_tags["color_tags"] and candidate_tags["color_tags"]:
            design_colors = set(design_tags["color_tags"])
            candidate_colors = set(candidate_tags["color_tags"])

            # Get user's skin tone if available
            user_pref = db.query(models.UserPreference).filter(
                models.UserPreference.user_id == user.id
            ).first()
            skin_tone = user_pref.skin_tone if user_pref else None
            undertone = user_pref.skin_undertone if user_pref else None

            if "裸色" in design_colors and "粉色" in candidate_colors:
                if skin_tone in ['fair', 'light']:
                    reasons.append("粉色系在你白皙肤色上会更显气色")
                else:
                    reasons.append("粉色系比裸色更显白")
                match_score += 15
            elif "深色" in design_colors and candidate_colors & {"裸色", "浅色", "米色"}:
                reasons.append("浅色系更适合日常通勤")
                match_score += 10
            elif "红色" in candidate_colors:
                reasons.append("红色系经典百搭，显白提气色")
                match_score += 12
            elif undertone == "warm" and candidate_colors & {"橘色", "珊瑚", "金色"}:
                reasons.append("暖调肤色配暖色系更和谐")
                match_score += 15
            elif undertone == "cool" and candidate_colors & {"粉色", "玫红", "紫色"}:
                reasons.append("冷调肤色配冷色系更显白")
                match_score += 15

        # Length-based recommendations
        if design_tags["length"] == "长" and candidate_tags["length"] == "短":
            reasons.append("短甲更方便打字、做家务")
            match_score += 8
        elif design_tags["length"] == "短" and candidate_tags["length"] == "长":
            reasons.append("长甲更显手指修长纤细")
            match_score += 8

        # Scene-based recommendations
        if design_tags["scene_tags"] and candidate_tags["scene_tags"]:
            if "日常" in design_tags["scene_tags"] and "派对" in candidate_tags["scene_tags"]:
                reasons.append("派对款更有设计感，适合特殊场合")
                match_score += 10
            elif "派对" in design_tags["scene_tags"] and "日常" in candidate_tags["scene_tags"]:
                reasons.append("日常款更低调实用，通勤也合适")
                match_score += 10
            elif "婚礼" in candidate_tags["scene_tags"]:
                reasons.append("精致优雅，适合重要场合")
                match_score += 12

        # Style-based recommendations
        if design_tags["style_tags"] and candidate_tags["style_tags"]:
            if "简约" in design_tags["style_tags"] and "华丽" in candidate_tags["style_tags"]:
                reasons.append("想换个风格？这款更有存在感")
                match_score += 8
            elif "猫眼" in candidate_tags["style_tags"]:
                reasons.append("猫眼效果独特，光泽感强")
                match_score += 10
            elif "渐变" in candidate_tags["style_tags"]:
                reasons.append("渐变设计自然柔和，显手长")
                match_score += 10

        # Popularity factor
        if candidate.is_hot:
            reasons.append(f"近期热门，{candidate.try_on_count}人试过")
            match_score += 5

        if reasons:
            recommendations.append({
                "design": candidate,
                "reason": reasons[0],
                "match_score": match_score
            })

    # Sort by match score
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    return recommendations[:limit]


@router.post("/similar", response_model=schemas.RecommendationResponse)
def get_recommendations(
    request: schemas.RecommendationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get recommendations based on a try-on record."""
    try_on = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.id == request.try_on_id
    ).first()

    if not try_on:
        raise HTTPException(status_code=404, detail="Try-on record not found")
    ensure_try_on_access(try_on, current_user)

    design = try_on.nail_design
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")

    # Similar designs
    similar = get_similar_designs(design, db, request.limit)
    similar_designs = [
        schemas.RecommendedDesign(
            design=design_to_response(d),
            reason="、".join(reasons) if reasons else "相似风格"
        )
        for d, score, reasons in similar
    ]

    # Better for you
    better = get_better_for_you(try_on, db, request.limit)
    better_designs = [
        schemas.RecommendedDesign(
            design=design_to_response(b["design"]),
            reason=b["reason"]
        )
        for b in better
    ]

    # Trending
    trending = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active",
        models.NailDesign.is_hot == True
    ).all()
    trending = filter_servable_designs(trending)
    trending = deduplicate_designs_by_image(sorted(trending, key=lambda design: int(design.id or 0)))
    trending = order_designs_by_completed_try_ons(db, trending)[:request.limit]

    return schemas.RecommendationResponse(
        similar_designs=similar_designs,
        better_for_you=better_designs,
        trending=[design_to_response(d) for d in trending]
    )


@router.get("/trending", response_model=List[schemas.NailDesignResponse])
def get_trending_designs(
    limit: int = 8,
    db: Session = Depends(get_db)
):
    """Get trending/hot designs."""
    designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active"
    ).all()
    designs = filter_servable_designs(designs)
    designs = deduplicate_designs_by_image(sorted(designs, key=lambda design: int(design.id or 0)))
    designs = order_designs_by_completed_try_ons(db, designs)[:limit]

    return [design_to_response(design) for design in designs]
