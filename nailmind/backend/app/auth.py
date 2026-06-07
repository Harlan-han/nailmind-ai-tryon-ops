"""Authentication helpers for local phone-code login."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.database import get_db


ALGORITHM = "HS256"
CODE_TTL_MINUTES = 10
MAX_LOGIN_CODE_ATTEMPTS = 5
DEFAULT_SECRET_KEY = "your-secret-key-change-this-in-production"

_login_codes: Dict[str, Dict[str, Any]] = {}
bearer_scheme = HTTPBearer(auto_error=False)


def clear_login_codes() -> None:
    _login_codes.clear()


def create_login_code(phone: str, user_type: str = "consumer") -> str:
    code = f"{random.randint(0, 999999):06d}"
    _login_codes[phone] = {
        "code": code,
        "user_type": user_type,
        "failed_attempts": 0,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=CODE_TTL_MINUTES),
    }
    return code


def revoke_login_code(phone: str) -> None:
    _login_codes.pop(phone, None)


def verify_login_code(phone: str, code: str, user_type: str = "consumer") -> bool:
    record = _login_codes.get(phone)
    if not record:
        return False
    if record["expires_at"] < datetime.now(timezone.utc):
        _login_codes.pop(phone, None)
        return False
    if record["code"] != code or record.get("user_type") != user_type:
        record["failed_attempts"] = record.get("failed_attempts", 0) + 1
        if record["failed_attempts"] >= MAX_LOGIN_CODE_ATTEMPTS:
            _login_codes.pop(phone, None)
        return False
    _login_codes.pop(phone, None)
    return True


def _safe_secret_key(settings) -> str:
    secret_key = (settings.SECRET_KEY or "").strip()
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SECRET_KEY must be configured",
        )
    if not settings.DEBUG and secret_key == DEFAULT_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SECRET_KEY must be changed before production auth",
        )
    return secret_key


def create_access_token(user: models.User, session_user_type: Optional[str] = None) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_type = session_user_type or user.user_type
    payload = {
        "sub": str(user.id),
        "phone": user.phone,
        "nickname": user.nickname or "",
        "user_type": user_type,
        "exp": expires_at,
    }
    return jwt.encode(payload, _safe_secret_key(settings), algorithm=ALGORITHM)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    settings = get_settings()
    try:
        payload = jwt.decode(credentials.credentials, _safe_secret_key(settings), algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        token_user_type = payload.get("user_type")
        token_nickname = payload.get("nickname")
    except (JWTError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if token_user_type not in {"consumer", "merchant", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token role",
        )
    scoped_user = SimpleNamespace(
        id=user.id,
        phone=user.phone,
        nickname=token_nickname if isinstance(token_nickname, str) and token_nickname else user.nickname,
        avatar_url=user.avatar_url,
        user_type=token_user_type,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
    return scoped_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    if not credentials:
        return None
    return get_current_user(credentials=credentials, db=db)


def require_operator(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.user_type not in {"merchant", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator permission required",
        )
    return current_user


def require_consumer(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.user_type != "consumer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consumer permission required",
        )
    return current_user
