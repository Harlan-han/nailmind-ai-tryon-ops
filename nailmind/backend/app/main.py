"""FastAPI main application."""
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import asyncio
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.database import engine, Base
from app.auth import get_current_user
from app import models
from app.routers import auth, users, designs, tryon, favorites, recommendations, operations, preferences, seasonal, consumer_assistant

settings = get_settings()

# Ensure uploads directory exists
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOADS_DIR, "designs"), exist_ok=True)
os.makedirs(os.path.join(UPLOADS_DIR, "hands"), exist_ok=True)

ALLOWED_HAND_PHOTO_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
ALLOWED_HAND_PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _cors_origins() -> list[str]:
    configured_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
    if settings.DEBUG:
        return configured_origins or ["*"]
    if not configured_origins or "*" in configured_origins:
        raise RuntimeError("CORS_ORIGINS must be explicitly configured when DEBUG=false")
    return configured_origins


def _looks_like_allowed_image(content: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return False


def _public_asset_url(path: str) -> str:
    base_url = settings.PUBLIC_ASSET_BASE_URL.strip().rstrip("/")
    normalized_path = "/" + path.lstrip("/")
    if not base_url:
        return normalized_path
    return f"{base_url}{normalized_path}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup: create tables
    Base.metadata.create_all(bind=engine)
    scheduler_task = asyncio.create_task(_operations_agent_scheduler())
    yield
    scheduler_task.cancel()
    # Shutdown
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


async def _operations_agent_scheduler():
    """Run lightweight in-process operations Agent schedules."""
    from app.operations_agent.agent_control import maybe_run_due_daily_report

    interval = max(10, settings.OPERATIONS_AGENT_SCHEDULER_INTERVAL_SECONDS)
    while True:
        try:
            maybe_run_due_daily_report()
        except Exception as exc:
            print(f"Operations Agent scheduler error: {exc}")
        await asyncio.sleep(interval)


app = FastAPI(
    title=settings.APP_NAME,
    description="NailMind AI Try-on and Smart Operations API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(designs.router, prefix="/api/designs", tags=["designs"])
app.include_router(tryon.router, prefix="/api/tryon", tags=["tryon"])
app.include_router(favorites.router, prefix="/api/favorites", tags=["favorites"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])
app.include_router(operations.router, prefix="/api/operations", tags=["operations"])
app.include_router(consumer_assistant.router, prefix="/api/consumer-assistant", tags=["consumer-assistant"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["preferences"])
app.include_router(seasonal.router, prefix="/api/seasonal", tags=["seasonal"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "nailmind-backend"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/api/upload/hand-photo")
async def upload_hand_photo(
    file: UploadFile = File(...),
    _current_user: models.User = Depends(get_current_user),
):
    """Upload a hand photo and return the URL."""
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_HAND_PHOTO_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP hand photos are supported")

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Hand photo exceeds max file size")
    if not _looks_like_allowed_image(content, content_type):
        raise HTTPException(status_code=400, detail="Uploaded hand photo is not a valid image file")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = Path(file.filename or "hand_photo").name
    safe_name = original_name.encode("ascii", "ignore").decode().strip().replace(" ", "_")
    if not safe_name:
        safe_name = "hand_photo"
    stem, suffix = os.path.splitext(safe_name)
    suffix = suffix.lower()
    if suffix not in ALLOWED_HAND_PHOTO_SUFFIXES:
        suffix = ALLOWED_HAND_PHOTO_CONTENT_TYPES[content_type]
    filename = f"hand_{timestamp}_{stem}{suffix}"
    file_path = os.path.join(UPLOADS_DIR, "hands", filename)

    with open(file_path, "wb") as f:
        f.write(content)

    upload_url = _public_asset_url(f"/uploads/hands/{filename}")
    return JSONResponse({
        "url": upload_url,
        "filename": filename
    })
