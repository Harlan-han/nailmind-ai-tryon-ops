"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== User Schemas ====================
class UserBase(BaseModel):
    phone: str
    nickname: Optional[str] = None
    user_type: str = "consumer"


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuthCodeRequest(BaseModel):
    phone: str = Field(..., min_length=6, max_length=20)
    nickname: Optional[str] = None
    user_type: str = "consumer"


class AuthLoginRequest(AuthCodeRequest):
    code: str = Field(..., min_length=4, max_length=8)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AuthCodeResponse(BaseModel):
    status: str
    expires_in_seconds: int
    debug_code: Optional[str] = None


# ==================== Hand Photo Schemas ====================
class HandPhotoBase(BaseModel):
    image_url: str


class HandPhotoCreate(HandPhotoBase):
    pass


class HandPhotoUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    crop_ratio: Optional[str] = Field(default=None, pattern=r"^(1:1|4:5|3:4)$")


class HandPhotoResponse(HandPhotoBase):
    id: int
    user_id: int
    thumbnail_url: Optional[str] = None
    status: str
    created_at: datetime
    name: Optional[str] = None
    crop_ratio: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Nail Design Schemas ====================
class NailDesignBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: str
    style_tags: Optional[List[str]] = []
    color_tags: Optional[List[str]] = []
    scene_tags: Optional[List[str]] = []
    length: Optional[str] = None
    shape: Optional[str] = None


class NailDesignCreate(NailDesignBase):
    pass


class NailDesignResponse(NailDesignBase):
    id: int
    thumbnail_url: Optional[str] = None
    status: str
    is_hot: bool
    is_new: bool
    view_count: int
    try_on_count: int
    favorite_count: int
    booking_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class NailDesignListRequest(BaseModel):
    style_tags: Optional[List[str]] = None
    color_tags: Optional[List[str]] = None
    scene_tags: Optional[List[str]] = None
    is_hot: Optional[bool] = None
    is_new: Optional[bool] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ==================== Try On Schemas ====================
class TryOnRequest(BaseModel):
    hand_photo_id: int
    nail_design_id: int


class TryOnResponse(BaseModel):
    id: int
    user_id: int
    hand_photo_id: int
    nail_design_id: int
    result_image_url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    is_favorite: bool
    is_candidate: bool
    has_booking_intent: bool
    created_at: datetime
    completed_at: Optional[datetime] = None
    nail_design: Optional[NailDesignResponse] = None

    class Config:
        from_attributes = True


class TryOnResultWebhook(BaseModel):
    try_on_id: int
    result_image_url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    provider: Optional[str] = None


class TryOnProgressResponse(BaseModel):
    try_on_id: int
    status: str
    progress: int
    phase: str
    message: str
    result_image_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: datetime
    elapsed_seconds: int
    updated_at: datetime


# ==================== Favorite Schemas ====================
class FavoriteCreate(BaseModel):
    nail_design_id: int
    try_on_record_id: Optional[int] = None


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    nail_design_id: int
    try_on_record_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Recommendation Schemas ====================
class RecommendationRequest(BaseModel):
    try_on_id: int
    limit: int = Field(default=4, ge=1, le=20)


class RecommendedDesign(BaseModel):
    design: NailDesignResponse
    reason: str  # e.g., " similar style", " better for your skin tone"


class RecommendationResponse(BaseModel):
    similar_designs: List[RecommendedDesign]
    better_for_you: List[RecommendedDesign]
    trending: List[NailDesignResponse]


# ==================== Booking Intent Schemas ====================
class BookingIntentCreate(BaseModel):
    try_on_record_id: int
    nail_design_id: int
    phone: str
    preferred_date: Optional[datetime] = None
    notes: Optional[str] = None


class BookingIntentResponse(BaseModel):
    id: int
    user_id: int
    try_on_record_id: int
    nail_design_id: int
    phone: str
    preferred_date: Optional[datetime] = None
    notes: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Trend/Operation Schemas ====================
class TrendOverview(BaseModel):
    today_try_ons: int
    today_favorites: int
    today_booking_intents: int
    hot_designs_count: int
    trending_styles: List[dict]


class MerchantHotDesign(BaseModel):
    id: int
    name: str
    image_url: str
    try_on_count: int


class MerchantActivity(BaseModel):
    event_key: str
    action: str
    detail: str
    time: str
    created_at: Optional[datetime] = None


class MerchantOverview(BaseModel):
    total_designs: int
    active_designs: int
    total_views: int
    total_try_ons: int
    failed_try_ons: int
    total_favorites: int
    conversion_rate: float
    hot_designs: List[MerchantHotDesign]
    recent_bookings: int
    recent_activity: List[MerchantActivity]


class HotDesign(BaseModel):
    design: NailDesignResponse
    growth_rate: float
    reason: str


class TrendAnalysisResponse(BaseModel):
    period: str
    hot_designs: List[HotDesign]
    style_distribution: dict
    daily_stats: List[dict]


class DailyReport(BaseModel):
    date: datetime
    summary: str
    highlights: List[str]
    alerts: List[str]
    recommendations: List[dict]
    copy_for_operation: str


class OperationsAssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    conversation_id: Optional[str] = None
    context: Optional[dict] = None


class OperationsAssistantEvidence(BaseModel):
    label: str
    value: str
    source: str


class OperationsAssistantAction(BaseModel):
    title: str
    reason: str
    priority: str
    risk: Optional[str] = None
    requires_confirmation: bool = True


class OperationsAssistantToolTrace(BaseModel):
    tool: str
    status: str
    summary: Optional[str] = None


class OperationsAssistantChatResponse(BaseModel):
    answer: str
    evidence: List[OperationsAssistantEvidence] = []
    recommended_actions: List[OperationsAssistantAction] = []
    tool_trace: List[OperationsAssistantToolTrace] = []
    confidence: str = "medium"


class OperationsAssistantSuggestionSyncRequest(BaseModel):
    source_message: Optional[str] = None
    answer: Optional[str] = None
    evidence: List[OperationsAssistantEvidence] = []
    actions: List[OperationsAssistantAction]


class OperationsAssistantExternalMessageRequest(BaseModel):
    channel: str = Field(..., min_length=1, max_length=40)
    sender: str = Field("external_operator", max_length=120)
    message: str = Field(..., min_length=1, max_length=1000)
    context: Optional[dict] = None


class OperationsAssistantExternalReply(BaseModel):
    channel: str
    delivery_channel: Optional[str] = None
    delivery_status: Optional[str] = None
    delivery_detail: Optional[str] = None
    sender: str
    reply_text: str
    evidence: List[OperationsAssistantEvidence] = []
    recommended_actions: List[OperationsAssistantAction] = []
    tool_trace: List[OperationsAssistantToolTrace] = []
    created_at: str


class OperationsAssistantWebhookRequest(BaseModel):
    channel: str = Field("feishu", max_length=40)
    sender: str = Field("external_operator", max_length=120)
    text: Optional[str] = Field(None, max_length=1000)
    message: Optional[str] = Field(None, max_length=1000)
    token: Optional[str] = None
    context: Optional[dict] = None


class OperationsAssistantCommandRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=300)
    assistant_payload: dict


class OperationsAssistantScheduleRequest(BaseModel):
    enabled: bool = True
    time: str = "09:30"
    channels: List[str] = ["feishu"]
    prompt: str = "生成今日运营日报"


class ConsumerAssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=800)
    conversation_id: Optional[str] = None
    context: Optional[dict] = None


class ConsumerAssistantRecommendation(BaseModel):
    id: int
    name: str
    image_url: str
    reason: str
    style_tags: List[str] = []


class ConsumerAssistantChatResponse(BaseModel):
    persona: str
    answer: str
    recommendations: List[ConsumerAssistantRecommendation] = []
    chips: List[str] = []
    conversation_id: str
    confidence: str = "medium"


# ==================== User Preference Schemas ====================
class PreferenceItem(BaseModel):
    name: str
    score: float
    count: int


class UserPreferenceResponse(BaseModel):
    id: int
    user_id: int
    preferred_styles: List[PreferenceItem] = []
    preferred_colors: List[PreferenceItem] = []
    preferred_scenes: List[PreferenceItem] = []
    skin_tone: Optional[str] = None
    skin_undertone: Optional[str] = None
    preferred_length: Optional[str] = None
    preferred_shape: Optional[str] = None
    total_try_ons: int = 0
    total_favorites: int = 0
    total_candidates: int = 0
    total_bookings: int = 0
    last_calculated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PersonalizedRecommendation(BaseModel):
    design: NailDesignResponse
    match_score: float
    reasons: List[str]
