"""Nail design management routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app import models, schemas
from app.auth import get_optional_current_user, require_operator
from app.services.design_visual_tags import (
    collect_visual_tags,
    deduplicate_designs_by_image,
    design_to_response,
    filter_servable_designs,
    has_servable_design_image,
    matches_design_filters,
)

router = APIRouter()

ALLOWED_DESIGN_STATUSES = {"active", "inactive"}
COMPLETED_TRY_ON_STATUSES = ("completed",)


def order_designs_by_completed_try_ons(db: Session, designs: list[models.NailDesign]) -> list[models.NailDesign]:
    """Rank user-facing designs by successful try-on demand, not raw task attempts."""
    design_ids = [design.id for design in designs]
    if not design_ids:
        return []

    rows = db.query(
        models.TryOnRecord.nail_design_id,
        func.count(models.TryOnRecord.id).label("completed_try_ons"),
    ).filter(
        models.TryOnRecord.nail_design_id.in_(design_ids),
        models.TryOnRecord.status.in_(COMPLETED_TRY_ON_STATUSES),
    ).group_by(models.TryOnRecord.nail_design_id).all()
    completed_counts = {row.nail_design_id: int(row.completed_try_ons or 0) for row in rows}

    return sorted(
        designs,
        key=lambda design: (
            completed_counts.get(design.id, 0),
            int(design.favorite_count or 0),
            int(design.try_on_count or 0),
        ),
        reverse=True,
    )


def include_recently_updated_designs(
    selected: list[models.NailDesign],
    candidates: list[models.NailDesign],
    limit: int,
    max_insertions: int = 1,
) -> list[models.NailDesign]:
    """Keep recent manual operations visible without letting stale counters dominate ranking."""
    selected_by_id = {design.id: design for design in selected}
    updated_candidates = sorted(
        [design for design in candidates if design.updated_at and design.id not in selected_by_id],
        key=lambda design: design.updated_at,
        reverse=True,
    )

    for design in updated_candidates[:max_insertions]:
        if len(selected) < limit:
            selected.append(design)
            selected_by_id[design.id] = design
            continue
        if selected:
            removed = selected.pop()
            selected_by_id.pop(removed.id, None)
        selected.append(design)
        selected_by_id[design.id] = design

    return selected


def _list_designs_impl(
    style_tags: Optional[List[str]] = Query(None),
    color_tags: Optional[List[str]] = Query(None),
    scene_tags: Optional[List[str]] = Query(None),
    q: Optional[str] = Query(None),
    is_hot: Optional[bool] = None,
    is_new: Optional[bool] = None,
    include_inactive: bool = False,
    only_servable: bool = False,
    dedupe_images: bool = False,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user),
):
    """List nail designs with filters."""
    if include_inactive:
        if not current_user or current_user.user_type not in {"merchant", "admin"}:
            raise HTTPException(status_code=403, detail="Cannot list inactive designs")
        query = db.query(models.NailDesign)
    else:
        query = db.query(models.NailDesign).filter(models.NailDesign.status == "active")

    if is_hot is not None:
        query = query.filter(models.NailDesign.is_hot == is_hot)

    if is_new is not None:
        query = query.filter(models.NailDesign.is_new == is_new)

    # Order by hot first, then new, then by try_on_count
    query = query.order_by(
        models.NailDesign.is_hot.desc(),
        models.NailDesign.is_new.desc(),
        models.NailDesign.try_on_count.desc()
    )

    raw_designs = query.all()
    if not include_inactive or only_servable:
        raw_designs = filter_servable_designs(raw_designs)
    if not include_inactive or dedupe_images:
        raw_designs = sorted(raw_designs, key=lambda design: int(design.id or 0))
        raw_designs = deduplicate_designs_by_image(raw_designs)
        raw_designs = sorted(
            raw_designs,
            key=lambda design: (
                bool(design.is_hot),
                bool(design.is_new),
                int(design.try_on_count or 0),
            ),
            reverse=True,
        )

    designs = [
        design_to_response(design)
        for design in raw_designs
    ]
    designs = [
        design
        for design in designs
        if matches_design_filters(design, style_tags, color_tags, scene_tags, q)
    ]
    paginated_designs = designs[offset:offset + limit]

    # Increment view count
    viewed_ids = [design["id"] for design in paginated_designs]
    if viewed_ids and not include_inactive:
        db.query(models.NailDesign).filter(models.NailDesign.id.in_(viewed_ids)).update(
            {models.NailDesign.view_count: models.NailDesign.view_count + 1},
            synchronize_session=False,
        )
    db.commit()

    return paginated_designs


@router.get("", response_model=List[schemas.NailDesignResponse])
@router.get("/", response_model=List[schemas.NailDesignResponse])
def list_designs(
    style_tags: Optional[List[str]] = Query(None),
    color_tags: Optional[List[str]] = Query(None),
    scene_tags: Optional[List[str]] = Query(None),
    q: Optional[str] = Query(None),
    is_hot: Optional[bool] = None,
    is_new: Optional[bool] = None,
    include_inactive: bool = False,
    only_servable: bool = False,
    dedupe_images: bool = False,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_current_user),
):
    return _list_designs_impl(
        style_tags=style_tags,
        color_tags=color_tags,
        scene_tags=scene_tags,
        q=q,
        is_hot=is_hot,
        is_new=is_new,
        include_inactive=include_inactive,
        only_servable=only_servable,
        dedupe_images=dedupe_images,
        limit=limit,
        offset=offset,
        db=db,
        current_user=current_user,
    )


@router.get("/hot", response_model=List[schemas.NailDesignResponse])
def get_hot_designs(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get hot/trending designs."""
    designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active",
        models.NailDesign.is_hot == True
    ).all()
    designs = filter_servable_designs(designs)
    designs = sorted(designs, key=lambda design: int(design.id or 0))
    designs = deduplicate_designs_by_image(designs)
    ranked_designs = order_designs_by_completed_try_ons(db, designs)
    designs = include_recently_updated_designs(ranked_designs[:limit], ranked_designs, limit)

    return [design_to_response(design) for design in designs]


@router.get("/new", response_model=List[schemas.NailDesignResponse])
def get_new_designs(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get new arrivals."""
    designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active",
        models.NailDesign.is_new == True
    ).order_by(models.NailDesign.created_at.desc()).all()
    designs = filter_servable_designs(designs)
    designs = sorted(designs, key=lambda design: int(design.id or 0))
    designs = deduplicate_designs_by_image(designs)
    designs = sorted(designs, key=lambda design: design.created_at, reverse=True)[:limit]

    return [design_to_response(design) for design in designs]


@router.get("/{design_id}", response_model=schemas.NailDesignResponse)
def get_design(design_id: int, db: Session = Depends(get_db)):
    """Get a specific design."""
    design = db.query(models.NailDesign).filter(
        models.NailDesign.id == design_id,
        models.NailDesign.status == "active"
    ).first()

    if not design or not has_servable_design_image(design):
        raise HTTPException(status_code=404, detail="Design not found")

    # Increment view count
    design.view_count += 1
    db.commit()

    return design_to_response(design)


@router.post("/", response_model=schemas.NailDesignResponse)
def create_design(
    design: schemas.NailDesignCreate,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Create a new design (for admin/operations)."""
    db_design = models.NailDesign(**design.model_dump())
    db.add(db_design)
    db.commit()
    db.refresh(db_design)
    return design_to_response(db_design)


@router.put("/{design_id}", response_model=schemas.NailDesignResponse)
def update_design(
    design_id: int,
    design: schemas.NailDesignCreate,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Update a design (for admin/operations)."""
    db_design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
    if not db_design:
        raise HTTPException(status_code=404, detail="Design not found")

    for key, value in design.model_dump().items():
        setattr(db_design, key, value)

    db.commit()
    db.refresh(db_design)
    return design_to_response(db_design)


@router.delete("/{design_id}")
def delete_design(
    design_id: int,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Delete a design (for admin/operations)."""
    db_design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
    if not db_design:
        raise HTTPException(status_code=404, detail="Design not found")

    db_design.status = "inactive"
    db.commit()
    db.refresh(db_design)
    return design_to_response(db_design)


@router.patch("/{design_id}/status", response_model=schemas.NailDesignResponse)
def update_design_status(
    design_id: int,
    status: str,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Update design status (active/inactive)."""
    if status not in ALLOWED_DESIGN_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid design status")

    db_design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
    if not db_design:
        raise HTTPException(status_code=404, detail="Design not found")

    db_design.status = status
    db.commit()
    db.refresh(db_design)
    return design_to_response(db_design)


@router.patch("/{design_id}/hot", response_model=schemas.NailDesignResponse)
def toggle_hot(
    design_id: int,
    is_hot: bool,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Toggle hot status for a design."""
    db_design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
    if not db_design:
        raise HTTPException(status_code=404, detail="Design not found")

    db_design.is_hot = is_hot
    db.commit()
    db.refresh(db_design)
    return design_to_response(db_design)


@router.patch("/{design_id}/new", response_model=schemas.NailDesignResponse)
def toggle_new(
    design_id: int,
    is_new: bool,
    db: Session = Depends(get_db),
    _operator: models.User = Depends(require_operator),
):
    """Toggle new status for a design."""
    db_design = db.query(models.NailDesign).filter(models.NailDesign.id == design_id).first()
    if not db_design:
        raise HTTPException(status_code=404, detail="Design not found")

    db_design.is_new = is_new
    db.commit()
    db.refresh(db_design)
    return design_to_response(db_design)


@router.get("/tags/styles")
def get_style_tags(db: Session = Depends(get_db)):
    """Get all available style tags."""
    designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active"
    ).all()
    designs = filter_servable_designs(designs)

    return {"tags": collect_visual_tags(designs, "style_tags")}


@router.get("/tags/colors")
def get_color_tags(db: Session = Depends(get_db)):
    """Get all available color tags."""
    designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active"
    ).all()
    designs = filter_servable_designs(designs)

    return {"tags": collect_visual_tags(designs, "color_tags")}


@router.get("/tags/scenes")
def get_scene_tags(db: Session = Depends(get_db)):
    """Get all available scene tags."""
    designs = db.query(models.NailDesign).filter(
        models.NailDesign.status == "active"
    ).all()
    designs = filter_servable_designs(designs)

    return {"tags": collect_visual_tags(designs, "scene_tags")}
