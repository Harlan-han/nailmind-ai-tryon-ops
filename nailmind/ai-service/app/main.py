"""AI Service main application - Advanced nail try-on with MediaPipe."""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import os
from datetime import datetime
import io
import json
import mimetypes
from urllib.parse import quote, urlsplit
import asyncio
import logging
import threading

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NailMind AI Service",
    description="AI-powered nail try-on generation service",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
BACKEND_WEBHOOK_URL = os.getenv("BACKEND_WEBHOOK_URL", "http://localhost:8004/api/tryon/webhook/result")


def resolve_backend_origin(webhook_url: str) -> str:
    """Resolve the backend origin used for source downloads and returned result URLs."""
    configured_origin = os.getenv("BACKEND_ORIGIN", "").strip().rstrip("/")
    if configured_origin:
        return configured_origin

    parsed = urlsplit(webhook_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return "http://localhost:8004"


BACKEND_ORIGIN = resolve_backend_origin(BACKEND_WEBHOOK_URL)


def resolve_backend_webhook_secret() -> str:
    """Prefer the sender-side secret name while keeping the old local name working."""
    return os.getenv("BACKEND_WEBHOOK_SECRET") or os.getenv("AI_WEBHOOK_SECRET", "")


BACKEND_WEBHOOK_SECRET = resolve_backend_webhook_secret()
# Save results to backend uploads so they are served from the same origin
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "backend", "uploads", "results"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# RunningHub workflow configuration. Keep API keys out of code and .env commits.
TRYON_PROVIDER = os.getenv("NAILMIND_TRYON_PROVIDER", "runninghub").strip().lower()
RUNNINGHUB_API_KEY = os.getenv("RUNNINGHUB_API_KEY", "")
RUNNINGHUB_BASE_URL = os.getenv("RUNNINGHUB_BASE_URL", "https://www.runninghub.cn/openapi/v2")
RUNNINGHUB_OUTPUTS_URL = os.getenv("RUNNINGHUB_OUTPUTS_URL", "https://www.runninghub.cn/task/openapi/outputs")
RUNNINGHUB_WORKFLOW_ID = os.getenv("RUNNINGHUB_WORKFLOW_ID", "2032743911923392514")
RUNNINGHUB_INSTANCE_TYPE = os.getenv("RUNNINGHUB_INSTANCE_TYPE", "default")
RUNNINGHUB_USE_PERSONAL_QUEUE = os.getenv("RUNNINGHUB_USE_PERSONAL_QUEUE", "false")
RUNNINGHUB_POLL_INTERVAL_SECONDS = float(os.getenv("RUNNINGHUB_POLL_INTERVAL_SECONDS", "5"))
RUNNINGHUB_TIMEOUT_SECONDS = int(os.getenv("RUNNINGHUB_TIMEOUT_SECONDS", "360"))
RUNNINGHUB_PROMPT = os.getenv(
    "RUNNINGHUB_PROMPT",
    "给 {image1} 中人物的手部指甲试戴 {image2} 中的美甲款式，自动适配每个指甲，"
    "仅修改 {image1} 中的手部指甲，其余部分保持不变，保持真实自然的光影和手部纹理。"
)
RUNNING_TASK_IDS: set[int] = set()
RUNNING_TASK_LOCK = threading.Lock()

# Initialize advanced processor
try:
    from app.advanced_processor import AdvancedNailTryOn, load_image_from_bytes, save_image_to_bytes
    try_on_generator = AdvancedNailTryOn()
    USE_ADVANCED = True
    print("Advanced nail try-on generator initialized successfully")
except Exception as e:
    print(f"Advanced processor failed to load: {e}")
    # Fallback to simple mode
    from app.utils.image_processor import NailTryOnGenerator, load_image_from_bytes, save_image_to_bytes
    try_on_generator = NailTryOnGenerator()
    USE_ADVANCED = False
    print("Using fallback processor")


class GenerateRequest(BaseModel):
    hand_photo_url: str
    design_image_url: str
    try_on_id: int


class GenerateResponse(BaseModel):
    try_on_id: int
    status: str
    result_url: Optional[str] = None
    message: str


def should_use_runninghub() -> bool:
    """Return whether to route try-on generation to RunningHub."""
    if TRYON_PROVIDER == "local":
        raise HTTPException(
            status_code=500,
            detail="Local try-on fallback is disabled. Configure RunningHub for AI try-on generation."
        )
    if TRYON_PROVIDER not in {"runninghub", "auto"}:
        raise HTTPException(
            status_code=500,
            detail=f"Unsupported NAILMIND_TRYON_PROVIDER: {TRYON_PROVIDER}"
        )
    if not RUNNINGHUB_API_KEY.strip():
        raise HTTPException(
            status_code=500,
            detail=(
                "RUNNINGHUB_API_KEY is required for RunningHub try-on generation. "
                "Set NAILMIND_TRYON_PROVIDER=local only when intentionally using local fallback."
            )
        )
    return True


def current_provider_label() -> str:
    """Return the configured try-on provider label without validating external credentials."""
    return "runninghub"


def to_backend_url(image_url: str) -> str:
    """Convert backend-relative upload paths to absolute URLs."""
    if image_url.startswith('/uploads'):
        # URL-encode the path to handle non-ASCII characters
        encoded_path = quote(image_url, safe='/')
        return f"{BACKEND_ORIGIN}{encoded_path}"
    return image_url


def to_backend_upload_url(path: str) -> str:
    """Build a public backend upload URL using the configured backend origin."""
    normalized_path = "/" + path.lstrip("/")
    return f"{BACKEND_ORIGIN}{normalized_path}"


def guess_filename(url: str, fallback: str) -> str:
    """Best-effort filename extraction from a URL or path."""
    name = url.split("?")[0].rstrip("/").split("/")[-1]
    return name or fallback


def normalize_content_type(filename: str, content_type: Optional[str]) -> str:
    """Return an image content type even when the source server reports a generic type."""
    guessed = mimetypes.guess_type(filename)[0]
    if guessed and guessed.startswith("image/"):
        return guessed
    if content_type and content_type.startswith("image/"):
        return content_type.split(";")[0]
    return "image/png"


async def download_source_image(image_url: str, fallback_name: str) -> tuple[str, bytes, str]:
    """Download a source image from backend/local URL without using proxy env vars."""
    resolved_url = to_backend_url(image_url)
    async with httpx.AsyncClient(trust_env=False, follow_redirects=True) as client:
        response = await client.get(resolved_url, timeout=30.0)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to download image: {resolved_url}")

    filename = guess_filename(resolved_url, fallback_name)
    content_type = normalize_content_type(filename, response.headers.get("content-type"))
    return filename, response.content, content_type


async def upload_runninghub_media(
    client: httpx.AsyncClient,
    filename: str,
    content: bytes,
    content_type: str,
) -> str:
    """Upload image bytes to RunningHub and return the workflow fileName."""
    response = await client.post(
        f"{RUNNINGHUB_BASE_URL}/media/upload/binary",
        headers={"Authorization": f"Bearer {RUNNINGHUB_API_KEY}"},
        files={"file": (filename, content, content_type)},
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") or {}
    file_name = data.get("fileName")
    if not file_name:
        raise HTTPException(status_code=502, detail=f"RunningHub upload did not return fileName: {payload}")
    return file_name


async def submit_runninghub_task(
    client: httpx.AsyncClient,
    hand_file_name: str,
    design_file_name: str,
) -> str:
    """Submit the nail transfer workflow and return the RunningHub task ID."""
    node_info_list = [
        {"nodeId": "1", "fieldName": "image", "fieldValue": hand_file_name},
        {"nodeId": "2", "fieldName": "image", "fieldValue": design_file_name},
        {"nodeId": "4", "fieldName": "text", "fieldValue": RUNNINGHUB_PROMPT},
    ]
    response = await client.post(
        f"{RUNNINGHUB_BASE_URL}/run/workflow/{RUNNINGHUB_WORKFLOW_ID}",
        headers={
            "Authorization": f"Bearer {RUNNINGHUB_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "addMetadata": True,
            "nodeInfoList": node_info_list,
            "instanceType": RUNNINGHUB_INSTANCE_TYPE,
            "usePersonalQueue": RUNNINGHUB_USE_PERSONAL_QUEUE,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()
    task_id = payload.get("taskId")
    if not task_id:
        raise HTTPException(status_code=502, detail=f"RunningHub run did not return taskId: {payload}")
    if payload.get("status") == "FAILED":
        raise HTTPException(status_code=502, detail=payload.get("errorMessage") or "RunningHub task submission failed")
    logger.info("RunningHub task submitted for workflow=%s task_id=%s", RUNNINGHUB_WORKFLOW_ID, task_id)
    return task_id


def exception_to_message(exc: Exception) -> str:
    """Return a user-visible failure message without losing FastAPI HTTPException.detail."""
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, str):
            return detail
        return json.dumps(detail, ensure_ascii=False)
    message = str(exc).strip()
    return message or exc.__class__.__name__


async def query_runninghub_until_done(client: httpx.AsyncClient, task_id: str) -> dict:
    """Poll RunningHub task status until success/failure/timeout."""
    deadline = datetime.now().timestamp() + RUNNINGHUB_TIMEOUT_SECONDS
    last_payload: dict = {}
    last_error = ""
    while datetime.now().timestamp() < deadline:
        try:
            response = await client.post(
                f"{RUNNINGHUB_BASE_URL}/query",
                headers={
                    "Authorization": f"Bearer {RUNNINGHUB_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"taskId": task_id},
                timeout=30.0,
            )
            response.raise_for_status()
            last_payload = response.json()
        except httpx.RequestError as exc:
            last_error = exception_to_message(exc)
            logger.warning("RunningHub query transient error for task_id=%s: %s", task_id, last_error)
            await asyncio.sleep(RUNNINGHUB_POLL_INTERVAL_SECONDS)
            continue

        status = (last_payload.get("status") or "").upper()
        logger.info(
            "RunningHub task status task_id=%s status=%s has_results=%s",
            task_id,
            status or "UNKNOWN",
            bool(last_payload.get("results")),
        )
        if status == "SUCCESS":
            return last_payload
        if status == "FAILED":
            raise HTTPException(
                status_code=502,
                detail=last_payload.get("errorMessage") or last_payload.get("failedReason") or "RunningHub task failed"
            )

        await asyncio.sleep(RUNNINGHUB_POLL_INTERVAL_SECONDS)

    suffix = f"; last error: {last_error}" if last_error else ""
    raise HTTPException(status_code=504, detail=f"RunningHub task timed out: {last_payload}{suffix}")


async def query_runninghub_task_outputs(client: httpx.AsyncClient, task_id: str) -> dict:
    """Fetch task outputs from RunningHub's output endpoint when /query has no results."""
    response = await client.post(
        RUNNINGHUB_OUTPUTS_URL,
        headers={
            "Authorization": f"Bearer {RUNNINGHUB_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "apiKey": RUNNINGHUB_API_KEY,
            "taskId": task_id,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    payload = response.json()
    logger.info(
        "RunningHub task outputs task_id=%s code=%s has_data=%s",
        task_id,
        payload.get("code"),
        bool(payload.get("data")),
    )
    return payload


def is_image_output_type(output_type: str) -> bool:
    if not output_type:
        return True
    normalized = output_type.lower().split(";")[0].strip()
    return normalized in {"png", "jpg", "jpeg", "webp", "image"} or normalized.startswith("image/")


def extract_result_url(payload: dict) -> str:
    """Extract the first image URL from RunningHub task results."""
    for collection_key in ("results", "data", "outputs"):
        collection = payload.get(collection_key)
        if not isinstance(collection, list):
            continue
        for item in collection:
            if isinstance(item, str):
                url = item
                output_type = ""
            elif isinstance(item, dict):
                url = item.get("url") or item.get("fileUrl") or item.get("file_url")
                output_type = (item.get("outputType") or item.get("fileType") or item.get("type") or "").lower()
            else:
                continue
            if url and is_image_output_type(output_type):
                return url
    raise HTTPException(status_code=502, detail=f"RunningHub task returned no image result: {payload}")


async def save_remote_result(client: httpx.AsyncClient, result_url: str, try_on_id: int) -> str:
    """Download RunningHub's temporary output URL and persist it in backend uploads."""
    response = await client.get(result_url, timeout=60.0, follow_redirects=True)
    response.raise_for_status()

    extension = mimetypes.guess_extension(response.headers.get("content-type", "").split(";")[0]) or ".png"
    result_filename = f"result_{try_on_id}_{int(datetime.now().timestamp())}{extension}"
    result_path = os.path.join(UPLOAD_DIR, result_filename)
    with open(result_path, "wb") as f:
        f.write(response.content)

    return to_backend_upload_url(f"/uploads/results/{result_filename}")


async def generate_try_on_with_runninghub(request: GenerateRequest) -> str:
    """Run the RunningHub NanoBanana2 nail transfer workflow."""
    hand_filename, hand_bytes, hand_content_type = await download_source_image(
        request.hand_photo_url,
        f"hand_{request.try_on_id}.png",
    )
    design_filename, design_bytes, design_content_type = await download_source_image(
        request.design_image_url,
        f"design_{request.try_on_id}.png",
    )

    async with httpx.AsyncClient(trust_env=False, follow_redirects=True) as client:
        hand_file_name = await upload_runninghub_media(client, hand_filename, hand_bytes, hand_content_type)
        design_file_name = await upload_runninghub_media(client, design_filename, design_bytes, design_content_type)
        task_id = await submit_runninghub_task(client, hand_file_name, design_file_name)
        task_payload = await query_runninghub_until_done(client, task_id)
        try:
            temporary_result_url = extract_result_url(task_payload)
        except HTTPException:
            outputs_payload = await query_runninghub_task_outputs(client, task_id)
            temporary_result_url = extract_result_url(outputs_payload)
        return await save_remote_result(client, temporary_result_url, request.try_on_id)


async def generate_try_on_locally(request: GenerateRequest) -> str:
    """Generate a local fallback try-on image using MediaPipe/OpenCV."""
    print(f"Starting local generation for try_on_id={request.try_on_id}")
    print(f"Hand photo URL: {request.hand_photo_url}")
    print(f"Design URL: {request.design_image_url}")

    hand_filename, hand_bytes, _ = await download_source_image(
        request.hand_photo_url,
        f"hand_{request.try_on_id}.png",
    )
    design_filename, design_bytes, _ = await download_source_image(
        request.design_image_url,
        f"design_{request.try_on_id}.png",
    )

    print(f"Loading images: {hand_filename}, {design_filename}")
    hand_image = load_image_from_bytes(hand_bytes)
    design_image = load_image_from_bytes(design_bytes)

    print(f"Hand image shape: {hand_image.shape}")
    print(f"Design image shape: {design_image.shape}")
    result_image = try_on_generator.process(hand_image, design_image)

    result_filename = f"result_{request.try_on_id}_{int(datetime.now().timestamp())}.jpg"
    result_path = os.path.join(UPLOAD_DIR, result_filename)
    result_bytes = save_image_to_bytes(result_image)
    with open(result_path, "wb") as f:
        f.write(result_bytes)

    return to_backend_upload_url(f"/uploads/results/{result_filename}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    provider = current_provider_label()
    runninghub_configured = bool(RUNNINGHUB_API_KEY.strip())
    configuration_error = None if runninghub_configured else "RUNNINGHUB_API_KEY is required for RunningHub try-on generation"
    return {
        "status": "healthy" if not configuration_error else "degraded",
        "service": "nailmind-ai",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "mode": "advanced" if USE_ADVANCED else "fallback",
        "processor": "mediapipe_hand_landmarks" if USE_ADVANCED else "simple_overlay",
        "provider": provider,
        "runninghub_configured": runninghub_configured,
        "runninghub_workflow_id": RUNNINGHUB_WORKFLOW_ID if provider == "runninghub" else None,
        "configuration_error": configuration_error,
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate_try_on(request: GenerateRequest):
    """Start nail try-on generation asynchronously."""
    with RUNNING_TASK_LOCK:
        if request.try_on_id in RUNNING_TASK_IDS:
            return GenerateResponse(
                try_on_id=request.try_on_id,
                status="processing",
                result_url=None,
                message="Try-on generation is already running"
            )
        RUNNING_TASK_IDS.add(request.try_on_id)

    asyncio.create_task(process_try_on_request(request))

    return GenerateResponse(
        try_on_id=request.try_on_id,
        status="processing",
        result_url=None,
        message="Try-on generation started"
    )


async def process_try_on_request(request: GenerateRequest):
    """Process a try-on request asynchronously with RunningHub as the only user-facing provider."""
    try:
        should_use_runninghub()
        result_url = await generate_try_on_with_runninghub(request)
        await notify_backend_result(
            request.try_on_id,
            status="completed",
            result_image_url=result_url,
            provider="runninghub",
        )
    except Exception as exc:
        error_message = exception_to_message(exc)
        logger.exception("Try-on generation failed for try_on_id=%s: %s", request.try_on_id, error_message)
        try:
            await notify_backend_result(
                request.try_on_id,
                status="failed",
                error_message=error_message,
                provider="runninghub",
            )
        except Exception as notify_exc:
            print(f"Failed to notify backend of try_on failure for try_on_id={request.try_on_id}: {notify_exc}")
    finally:
        with RUNNING_TASK_LOCK:
            RUNNING_TASK_IDS.discard(request.try_on_id)


@app.post("/generate/upload")
async def generate_try_on_upload(
    hand_photo: UploadFile = File(...),
    design_image: UploadFile = File(...),
    try_on_id: int = 0
):
    """Generate try-on from uploaded files."""
    try:
        hand_bytes = await hand_photo.read()
        design_bytes = await design_image.read()

        hand_image = load_image_from_bytes(hand_bytes)
        design_image = load_image_from_bytes(design_bytes)

        result_image = try_on_generator.process(hand_image, design_image)
        result_bytes = save_image_to_bytes(result_image)

        return StreamingResponse(
            io.BytesIO(result_bytes),
            media_type="image/jpeg"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.post("/analyze/hand")
async def analyze_hand(image: UploadFile = File(...)):
    """Analyze hand photo quality."""
    try:
        image_bytes = await image.read()
        hand_image = load_image_from_bytes(image_bytes)

        result = try_on_generator.analyze_hand_quality(hand_image)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/results/{filename}")
async def get_result_image(filename: str):
    """Get generated result image."""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    with open(file_path, "rb") as f:
        return StreamingResponse(f, media_type="image/jpeg")


@app.get("/uploads/results/{filename}")
async def get_result_image_alias(filename: str):
    """Alias for results served through backend path."""
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    with open(file_path, "rb") as f:
        return StreamingResponse(f, media_type="image/jpeg")


@app.get("/models/status")
async def get_model_status():
    """Get status of loaded AI models."""
    return {
        "hand_detection": {
            "loaded": USE_ADVANCED,
            "model": "mediapipe_hands" if USE_ADVANCED else "none",
            "version": "0.10.0" if USE_ADVANCED else None
        },
        "nail_segmentation": {
            "loaded": USE_ADVANCED,
            "method": "geometric_estimation" if USE_ADVANCED else "none"
        },
        "blending": {
            "loaded": True,
            "method": "poisson_like" if USE_ADVANCED else "simple_alpha"
        },
        "status": "ready",
        "mode": "advanced" if USE_ADVANCED else "fallback"
    }


async def notify_backend_result(
    try_on_id: int,
    status: str,
    result_image_url: Optional[str] = None,
    error_message: Optional[str] = None,
    provider: Optional[str] = None,
):
    """Notify backend of try-on status changes."""
    payload = {
        "try_on_id": try_on_id,
        "result_image_url": result_image_url,
        "status": status,
        "error_message": error_message,
        "provider": provider,
    }
    async with httpx.AsyncClient(trust_env=False) as client:
        headers = {"X-NailMind-Webhook-Secret": BACKEND_WEBHOOK_SECRET} if BACKEND_WEBHOOK_SECRET else None
        await client.post(BACKEND_WEBHOOK_URL, json=payload, headers=headers, timeout=30.0)
        print(f"Webhook notification sent for try_on_id={try_on_id} status={status}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
