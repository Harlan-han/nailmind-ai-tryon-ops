"""Phone number normalization utilities."""

from fastapi import HTTPException


def digits_only(value: str | None) -> str:
    return "".join(char for char in (value or "").strip() if char.isdigit())


def normalize_phone(phone: str) -> str:
    normalized = digits_only(phone)
    if not normalized or len(normalized) < 6 or len(normalized) > 20:
        raise HTTPException(status_code=400, detail="Phone is required")
    return normalized
