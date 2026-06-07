"""Database models for NailMind."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """User model for both C-end and B-end."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, index=True)
    nickname = Column(String(100))
    avatar_url = Column(String(500))
    user_type = Column(String(20), default="consumer")  # consumer, merchant, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    hand_photos = relationship("HandPhoto", back_populates="user")
    try_on_records = relationship("TryOnRecord", back_populates="user")
    favorites = relationship("Favorite", back_populates="user")


class HandPhoto(Base):
    """User uploaded hand photos."""
    __tablename__ = "hand_photos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    status = Column(String(20), default="active")  # active, deleted
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="hand_photos")
    try_on_records = relationship("TryOnRecord", back_populates="hand_photo")


class NailDesign(Base):
    """Nail design styles/款式."""
    __tablename__ = "nail_designs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))

    # Style attributes
    style_tags = Column(JSON)  # ["法式", "渐变", "猫眼"]
    color_tags = Column(JSON)  # ["裸色", "粉色", "红色"]
    scene_tags = Column(JSON)  # ["日常", "婚礼", "派对"]
    length = Column(String(20))  # short, medium, long
    shape = Column(String(20))  # round, square, oval, almond

    # Status
    status = Column(String(20), default="active")  # active, inactive, featured
    is_hot = Column(Boolean, default=False)
    is_new = Column(Boolean, default=False)

    # Statistics
    view_count = Column(Integer, default=0)
    try_on_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    booking_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    try_on_records = relationship("TryOnRecord", back_populates="nail_design")


class TryOnRecord(Base):
    """AI try-on generation records."""
    __tablename__ = "try_on_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    hand_photo_id = Column(Integer, ForeignKey("hand_photos.id"))
    nail_design_id = Column(Integer, ForeignKey("nail_designs.id"))

    # Results
    result_image_url = Column(String(500))
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)

    # User actions
    is_favorite = Column(Boolean, default=False)
    is_candidate = Column(Boolean, default=False)
    has_booking_intent = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="try_on_records")
    hand_photo = relationship("HandPhoto", back_populates="try_on_records")
    nail_design = relationship("NailDesign", back_populates="try_on_records")


class Favorite(Base):
    """User favorites collection."""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    nail_design_id = Column(Integer, ForeignKey("nail_designs.id"))
    try_on_record_id = Column(Integer, ForeignKey("try_on_records.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="favorites")


class TrendDaily(Base):
    """Daily trend statistics for operations."""
    __tablename__ = "trend_daily"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), index=True)

    # Overview metrics
    total_try_ons = Column(Integer, default=0)
    total_favorites = Column(Integer, default=0)
    total_booking_intents = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)

    # Breakdown
    style_trend = Column(JSON)  # {"法式": 120, "渐变": 98, ...}
    color_trend = Column(JSON)
    hot_designs = Column(JSON)  # [design_id, ...]

    # AI analysis
    ai_summary = Column(Text)
    ai_recommendations = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BookingIntent(Base):
    """User booking intentions."""
    __tablename__ = "booking_intents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    try_on_record_id = Column(Integer, ForeignKey("try_on_records.id"))
    nail_design_id = Column(Integer, ForeignKey("nail_designs.id"))

    # Contact info
    phone = Column(String(20))
    preferred_date = Column(DateTime(timezone=True))
    notes = Column(Text)

    status = Column(String(20), default="pending")  # pending, contacted, confirmed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserPreference(Base):
    """User preference profile based on behavior analysis."""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # Preferred styles (derived from favorites and try-ons)
    preferred_styles = Column(JSON, default=list)  # [{"style": "法式", "score": 0.85}, ...]
    preferred_colors = Column(JSON, default=list)   # [{"color": "裸色", "score": 0.72}, ...]
    preferred_scenes = Column(JSON, default=list)  # [{"scene": "日常", "score": 0.90}, ...]

    # Skin tone analysis (if available)
    skin_tone = Column(String(20))  # fair, light, medium, tan, dark
    skin_undertone = Column(String(20))  # warm, cool, neutral

    # Shape/length preferences
    preferred_length = Column(String(20))  # short, medium, long
    preferred_shape = Column(String(20))  # round, square, oval, almond

    # Activity patterns
    total_try_ons = Column(Integer, default=0)
    total_favorites = Column(Integer, default=0)
    total_candidates = Column(Integer, default=0)
    total_bookings = Column(Integer, default=0)

    # Last updated
    last_calculated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="preference")
