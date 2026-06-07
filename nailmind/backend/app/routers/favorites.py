"""Favorites management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter()

COMPLETED_TRY_ON_STATUSES = ("completed",)


def ensure_active_design(db: Session, design_id: int) -> models.NailDesign:
    design = db.query(models.NailDesign).filter(
        models.NailDesign.id == design_id,
        models.NailDesign.status == "active",
    ).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    return design


def ensure_ready_owned_try_on(
    db: Session,
    try_on_record_id: int | None,
    design_id: int,
    current_user: models.User,
) -> models.TryOnRecord | None:
    if not try_on_record_id:
        return None

    try_on = db.query(models.TryOnRecord).filter(
        models.TryOnRecord.id == try_on_record_id
    ).first()
    if not try_on:
        raise HTTPException(status_code=404, detail="Try-on record not found")
    if try_on.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot favorite another user's try-on record")
    if try_on.nail_design_id != design_id:
        raise HTTPException(status_code=400, detail="Try-on record does not match design")
    if try_on.status not in COMPLETED_TRY_ON_STATUSES or not try_on.result_image_url:
        raise HTTPException(status_code=400, detail="Try-on result is not ready for user intent")
    return try_on


@router.get("/user/{user_id}", response_model=List[schemas.FavoriteResponse])
def get_user_favorites(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all favorites for a user."""
    if user_id != current_user.id and current_user.user_type not in {"merchant", "admin"}:
        raise HTTPException(status_code=403, detail="Cannot read another user's favorites")
    favorites = db.query(models.Favorite).filter(
        models.Favorite.user_id == user_id
    ).order_by(models.Favorite.created_at.desc()).all()

    return favorites


@router.post("/", response_model=schemas.FavoriteResponse)
def add_favorite(
    favorite: schemas.FavoriteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add a design to favorites."""
    design = ensure_active_design(db, favorite.nail_design_id)
    try_on = ensure_ready_owned_try_on(
        db,
        favorite.try_on_record_id,
        favorite.nail_design_id,
        current_user,
    )

    # Check if already favorited
    existing = db.query(models.Favorite).filter(
        models.Favorite.user_id == current_user.id,
        models.Favorite.nail_design_id == favorite.nail_design_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already in favorites")

    db_favorite = models.Favorite(
        user_id=current_user.id,
        nail_design_id=favorite.nail_design_id,
        try_on_record_id=favorite.try_on_record_id
    )
    db.add(db_favorite)
    if try_on:
        try_on.is_favorite = True

    # Update design favorite count
    design.favorite_count += 1

    db.commit()
    db.refresh(db_favorite)

    return db_favorite


@router.delete("/{favorite_id}")
def remove_favorite(
    favorite_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Remove a favorite."""
    favorite = db.query(models.Favorite).filter(
        models.Favorite.id == favorite_id
    ).first()

    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    if favorite.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot remove another user's favorite")

    # Update design favorite count
    design = db.query(models.NailDesign).filter(
        models.NailDesign.id == favorite.nail_design_id
    ).first()
    if design:
        design.favorite_count = max(0, design.favorite_count - 1)
    if favorite.try_on_record_id:
        try_on = db.query(models.TryOnRecord).filter(
            models.TryOnRecord.id == favorite.try_on_record_id,
            models.TryOnRecord.user_id == current_user.id,
        ).first()
        if try_on:
            try_on.is_favorite = False

    db.delete(favorite)
    db.commit()

    return {"status": "success"}
