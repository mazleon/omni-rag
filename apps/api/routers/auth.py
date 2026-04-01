import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from core.db import get_db_session
from core.models import User, Org

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    org_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict[str, Any]


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    org_id: str


def create_access_token(user_id: uuid.UUID, org_id: uuid.UUID) -> tuple[str, datetime]:
    expires = datetime.utcnow() + timedelta(hours=24)
    payload = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "exp": expires,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token, expires


def verify_token(credentials: HTTPAuthorizationCredentials) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    payload = verify_token(credentials)
    user_id = uuid.UUID(payload["sub"])

    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    org = None
    if user_data.org_name:
        org = Org(
            id=uuid.uuid4(),
            name=user_data.org_name,
            slug=user_data.org_name.lower().replace(" ", "-"),
        )
        session.add(org)
        await session.flush()
    else:
        result = await session.execute(
            select(Org).where(Org.slug == "default")
        )
        org = result.scalar_one_or_none()
        if not org:
            org = Org(
                id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                name="Default Organization",
                slug="default",
            )
            session.add(org)
            await session.flush()

    user = User(
        id=uuid.uuid4(),
        org_id=org.id,
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=bcrypt.hash(user_data.password),
        role="admin" if not existing_user else "member",
    )
    session.add(user)
    await session.commit()

    access_token, expires = create_access_token(user.id, user.org_id)

    return TokenResponse(
        access_token=access_token,
        expires_in=int((expires - datetime.utcnow()).total_seconds()),
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "org_id": str(user.org_id),
        },
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not bcrypt.verify(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token, expires = create_access_token(user.id, user.org_id)

    return TokenResponse(
        access_token=access_token,
        expires_in=int((expires - datetime.utcnow()).total_seconds()),
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "org_id": str(user.org_id),
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        org_id=str(current_user.org_id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_user: User = Depends(get_current_active_user),
):
    access_token, expires = create_access_token(current_user.id, current_user.org_id)

    return TokenResponse(
        access_token=access_token,
        expires_in=int((expires - datetime.utcnow()).total_seconds()),
        user={
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "org_id": str(current_user.org_id),
        },
    )