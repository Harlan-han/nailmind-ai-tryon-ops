"""Authentication routes."""
import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import (
    CODE_TTL_MINUTES,
    create_access_token,
    create_login_code,
    get_current_user,
    revoke_login_code,
    verify_login_code,
)
from app.database import get_db
from app.config import get_settings
from app.services.phone import digits_only, normalize_phone

router = APIRouter()


def _normalize_user_type(user_type: str) -> str:
    return user_type if user_type in {"consumer", "merchant", "admin"} else "consumer"


def _operator_phone_set() -> set[str]:
    settings = get_settings()
    return {
        normalized
        for phone in settings.OPERATOR_PHONES.split(",")
        if (normalized := digits_only(phone))
    }


def _resolve_login_user_type(phone: str, requested_user_type: str) -> str:
    user_type = _normalize_user_type(requested_user_type)
    if user_type not in {"merchant", "admin"}:
        return "consumer"

    settings = get_settings()
    operator_phones = _operator_phone_set()
    if operator_phones:
        if phone in operator_phones:
            return user_type
        raise HTTPException(status_code=403, detail="Phone is not allowed to login as operator")

    if settings.DEBUG:
        return user_type

    raise HTTPException(status_code=403, detail="Operator login is not configured")


def _send_login_code(phone: str, code: str) -> None:
    settings = get_settings()
    provider = settings.SMS_PROVIDER.lower()
    if provider == "debug":
        if settings.DEBUG:
            return
        raise HTTPException(status_code=503, detail="Debug SMS provider is disabled outside DEBUG mode")
    if provider == "none":
        raise HTTPException(status_code=503, detail="SMS provider is not configured")
    if provider == "webhook":
        webhook_url = settings.SMS_WEBHOOK_URL.strip()
        if not webhook_url:
            raise HTTPException(status_code=503, detail="SMS webhook URL is not configured")

        payload = {
            "phone": phone,
            "code": code,
            "purpose": "login",
            "expires_in_seconds": CODE_TTL_MINUTES * 60,
        }
        request = Request(
            webhook_url,
            data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=5) as response:
                if response.status < 200 or response.status >= 300:
                    raise HTTPException(status_code=503, detail="SMS webhook delivery failed")
        except HTTPException:
            raise
        except (OSError, URLError) as exc:
            raise HTTPException(status_code=503, detail="SMS webhook delivery failed") from exc
        return
    raise HTTPException(status_code=503, detail=f"Unsupported SMS provider: {settings.SMS_PROVIDER}")


def _user_response_for_session(user: models.User, user_type: str) -> dict:
    data = schemas.UserResponse.model_validate(user).model_dump()
    data["user_type"] = user_type
    return data


@router.post("/request-code", response_model=schemas.AuthCodeResponse)
def request_login_code(request: schemas.AuthCodeRequest):
    """Request a local phone login code.

    The debug code is returned for local development. Replace this with an SMS
    provider adapter before production launch.
    """
    settings = get_settings()
    phone = normalize_phone(request.phone)
    user_type = _resolve_login_user_type(phone, request.user_type)
    code = create_login_code(phone, user_type)
    try:
        _send_login_code(phone, code)
    except HTTPException:
        revoke_login_code(phone)
        raise
    return {
        "status": "sent",
        "expires_in_seconds": CODE_TTL_MINUTES * 60,
        "debug_code": code if settings.DEBUG else None,
    }


@router.post("/login", response_model=schemas.AuthTokenResponse)
def login(request: schemas.AuthLoginRequest, db: Session = Depends(get_db)):
    """Login or register with a phone verification code."""
    phone = normalize_phone(request.phone)
    user_type = _resolve_login_user_type(phone, request.user_type)
    if not verify_login_code(phone, request.code, user_type):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    user = db.query(models.User).filter(models.User.phone == phone).first()
    if not user:
        user = models.User(
            phone=phone,
            nickname=request.nickname or f"用户{phone[-4:]}",
            user_type=user_type,
        )
        db.add(user)
    else:
        if request.nickname:
            user.nickname = request.nickname
        if user_type in {"merchant", "admin"}:
            user.user_type = user_type
        else:
            user.user_type = user.user_type or user_type
    db.commit()
    db.refresh(user)

    return {
        "access_token": create_access_token(user, user_type),
        "token_type": "bearer",
        "user": _user_response_for_session(user, user_type),
    }


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Get the current authenticated user."""
    return current_user
