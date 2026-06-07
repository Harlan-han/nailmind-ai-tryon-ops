"""User management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.hand_photo_presets import get_hand_photo_preset, list_available_hand_photo_presets
from app.services.hand_photo_meta import delete_hand_photo_meta, get_hand_photo_meta, update_hand_photo_meta
from app.services.phone import normalize_phone

router = APIRouter()


def ensure_user_access(user_id: int, current_user: models.User) -> None:
    """Allow users to read/write themselves while operators can inspect support cases."""
    if user_id != current_user.id and current_user.user_type not in {"merchant", "admin"}:
        raise HTTPException(status_code=403, detail="Cannot access another user's profile")


def hand_photo_to_response(photo: models.HandPhoto) -> dict:
    meta = get_hand_photo_meta(photo.id)
    return {
        "id": photo.id,
        "user_id": photo.user_id,
        "image_url": photo.image_url,
        "thumbnail_url": photo.thumbnail_url,
        "status": photo.status,
        "created_at": photo.created_at,
        "name": meta.get("name"),
        "crop_ratio": meta.get("crop_ratio"),
    }


def get_current_user_hand_photo(photo_id: int, db: Session, current_user: models.User) -> models.HandPhoto:
    photo = db.query(models.HandPhoto).filter(
        models.HandPhoto.id == photo_id,
        models.HandPhoto.user_id == current_user.id,
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Hand photo not found")
    return photo


@router.get("/me/hand-photo-presets")
def list_my_hand_photo_presets(
    _current_user: models.User = Depends(get_current_user),
):
    """List official hand photo presets that can be saved as the current user's profile."""
    return [
        {
            "id": preset.id,
            "name": preset.name,
            "image_url": preset.image_url,
            "tags": preset.tags,
            "crop_ratio": preset.crop_ratio,
        }
        for preset in list_available_hand_photo_presets()
    ]


@router.post("/me/hand-photo-presets/{preset_id}/use", response_model=schemas.HandPhotoResponse)
def use_my_hand_photo_preset(
    preset_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Save one official preset as the current user's reusable hand photo profile."""
    preset = get_hand_photo_preset(preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Hand photo preset not found")

    photo = db.query(models.HandPhoto).filter(
        models.HandPhoto.user_id == current_user.id,
        models.HandPhoto.image_url == preset.image_url,
        models.HandPhoto.status == "active",
    ).first()
    if not photo:
        photo = models.HandPhoto(user_id=current_user.id, image_url=preset.image_url)
        db.add(photo)
        db.commit()
        db.refresh(photo)

    update_hand_photo_meta(photo.id, {
        "name": preset.name,
        "crop_ratio": preset.crop_ratio,
    })
    return hand_photo_to_response(photo)


@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    if user.user_type != "consumer":
        raise HTTPException(status_code=400, detail="Public user creation only supports consumer accounts")

    phone = normalize_phone(user.phone)
    db_user = db.query(models.User).filter(models.User.phone == phone).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    user_data = user.model_dump(exclude={"user_type"})
    user_data["phone"] = phone
    db_user = models.User(**user_data, user_type="consumer")
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/phone/{phone}", response_model=schemas.UserResponse)
def get_user_by_phone(
    phone: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get user by phone number."""
    normalized_phone = normalize_phone(phone)
    user = db.query(models.User).filter(models.User.phone == normalized_phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_user_access(user.id, current_user)
    return user


@router.post("/me/hand-photos", response_model=schemas.HandPhotoResponse)
def upload_my_hand_photo(
    photo: schemas.HandPhotoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Upload a hand photo for the authenticated user."""
    db_photo = models.HandPhoto(user_id=current_user.id, **photo.model_dump())
    db.add(db_photo)
    db.commit()
    db.refresh(db_photo)
    return hand_photo_to_response(db_photo)


@router.get("/me/hand-photos", response_model=List[schemas.HandPhotoResponse])
def get_my_hand_photos(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all hand photos for the authenticated user."""
    photos = db.query(models.HandPhoto).filter(
        models.HandPhoto.user_id == current_user.id,
        models.HandPhoto.status == "active"
    ).order_by(models.HandPhoto.created_at.desc()).all()
    return [hand_photo_to_response(photo) for photo in photos]


@router.patch("/me/hand-photos/{photo_id}", response_model=schemas.HandPhotoResponse)
def update_my_hand_photo(
    photo_id: int,
    payload: schemas.HandPhotoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update display metadata for one authenticated user's hand photo."""
    photo = get_current_user_hand_photo(photo_id, db, current_user)
    if photo.status != "active":
        raise HTTPException(status_code=404, detail="Hand photo not found")
    update_hand_photo_meta(photo.id, payload.model_dump(exclude_unset=True))
    return hand_photo_to_response(photo)


@router.delete("/me/hand-photos/{photo_id}", response_model=schemas.HandPhotoResponse)
def delete_my_hand_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Archive one authenticated user's hand photo."""
    photo = get_current_user_hand_photo(photo_id, db, current_user)
    photo.status = "deleted"
    db.commit()
    db.refresh(photo)
    delete_hand_photo_meta(photo.id)
    return hand_photo_to_response(photo)


@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get user by ID."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_user_access(user.id, current_user)
    return user


@router.post("/{user_id}/hand-photos", response_model=schemas.HandPhotoResponse)
def upload_hand_photo(
    user_id: int,
    photo: schemas.HandPhotoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Upload a hand photo for a user."""
    ensure_user_access(user_id, current_user)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_photo = models.HandPhoto(user_id=user_id, **photo.model_dump())
    db.add(db_photo)
    db.commit()
    db.refresh(db_photo)
    return hand_photo_to_response(db_photo)


@router.get("/{user_id}/hand-photos", response_model=List[schemas.HandPhotoResponse])
def get_user_hand_photos(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all hand photos for a user."""
    ensure_user_access(user_id, current_user)
    photos = db.query(models.HandPhoto).filter(
        models.HandPhoto.user_id == user_id,
        models.HandPhoto.status == "active"
    ).order_by(models.HandPhoto.created_at.desc()).all()
    return [hand_photo_to_response(photo) for photo in photos]
