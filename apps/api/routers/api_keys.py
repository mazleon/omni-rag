import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db, set_rls_context
from core.models import Org, User, ApiKey
from apps.api.routers.auth import get_current_active_user

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class ApiKeyCreateRequest(BaseModel):
    name: str
    rate_limit: int = 100
    rate_window_seconds: int = 60
    scopes: list[str] | None = None
    expires_in_days: int | None = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    rate_limit: int
    rate_window_seconds: int
    scopes: list[str] | None
    expires_at: str | None
    is_active: bool
    last_used_at: str | None
    created_at: str


class ApiKeyWithSecretResponse(BaseModel):
    id: str
    name: str
    api_key: str
    prefix: str
    rate_limit: int
    rate_window_seconds: int
    scopes: list[str] | None
    expires_at: str | None
    created_at: str


def _hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_api_key() -> str:
    return f"onr_{secrets.token_urlsafe(32)}"


def _get_key_prefix(key: str) -> str:
    return key[:16]


async def get_current_org(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Org:
    result = await session.execute(select(Org).where(Org.id == current_user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("", response_model=ApiKeyWithSecretResponse, status_code=201)
async def create_api_key(
    request: ApiKeyCreateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)
    api_key = _generate_api_key()
    key_hash = _hash_api_key(api_key)
    prefix = _get_key_prefix(api_key)
    
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
    
    scopes_str = ",".join(request.scopes) if request.scopes else None
    
    api_key_record = ApiKey(
        id=uuid.uuid4(),
        org_id=org.id,
        user_id=user.id,
        key_hash=key_hash,
        name=request.name,
        prefix=prefix,
        rate_limit=request.rate_limit,
        rate_window_seconds=request.rate_window_seconds,
        scopes=scopes_str,
        expires_at=expires_at,
    )
    
    session.add(api_key_record)
    await session.commit()
    
    return ApiKeyWithSecretResponse(
        id=str(api_key_record.id),
        name=api_key_record.name,
        api_key=api_key,
        prefix=prefix,
        rate_limit=api_key_record.rate_limit,
        rate_window_seconds=api_key_record.rate_window_seconds,
        scopes=request.scopes,
        expires_at=expires_at.isoformat() if expires_at else None,
        created_at=api_key_record.created_at.isoformat(),
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)
    result = await session.execute(
        select(ApiKey)
        .where(ApiKey.org_id == org.id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    
    return [
        ApiKeyResponse(
            id=str(k.id),
            name=k.name,
            prefix=k.prefix,
            rate_limit=k.rate_limit,
            rate_window_seconds=k.rate_window_seconds,
            scopes=k.scopes.split(",") if k.scopes else None,
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            is_active=k.is_active,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.org_id == org.id,
        )
    )
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    return ApiKeyResponse(
        id=str(key.id),
        name=key.name,
        prefix=key.prefix,
        rate_limit=key.rate_limit,
        rate_window_seconds=key.rate_window_seconds,
        scopes=key.scopes.split(",") if key.scopes else None,
        expires_at=key.expires_at.isoformat() if key.expires_at else None,
        is_active=key.is_active,
        last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        created_at=key.created_at.isoformat(),
    )


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.org_id == org.id,
        )
    )
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = False
    await session.commit()
    
    return {"message": "API key revoked", "key_id": str(key_id)}


async def verify_api_key(
    api_key: str,
    session: AsyncSession,
) -> ApiKey | None:
    key_hash = _hash_api_key(api_key)
    
    result = await session.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    )
    key = result.scalar_one_or_none()
    
    if not key:
        return None
    
    if not key.is_active:
        return None
    
    if key.expires_at and key.expires_at < datetime.utcnow():
        return None
    
    key.last_used_at = datetime.utcnow()
    await session.commit()
    
    return key
