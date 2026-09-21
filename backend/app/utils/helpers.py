"""
Shared utilities: auth dependency, card catalog loader, JSON field helpers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

# Required — raises 401 when no token is provided
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Optional — returns None instead of raising 401 when no token present
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# ── Auth dependency ────────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if not user_id:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exc
    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Returns the authenticated User or None for unauthenticated requests."""
    if not token:
        return None
    user_id = decode_access_token(token)
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user


# ── Card catalog loader ────────────────────────────────────────────────────────

_CATALOG_PATH = Path(__file__).parent.parent.parent / "data" / "card_catalog.json"


def load_card_catalog() -> List[dict]:
    """Load card catalog from JSON file."""
    with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cards", [])


# ── JSON field helpers ─────────────────────────────────────────────────────────

def parse_json_field(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def dump_json_field(value) -> str:
    return json.dumps(value, ensure_ascii=False)
