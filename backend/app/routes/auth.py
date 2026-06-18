from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.auth.dependencies import get_current_user
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.mongodb import get_database
from app.models.auth import AuthResponse, RefreshTokenRequest, UserCreate, UserLogin, UserResponse


router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _serialize_user(user: dict) -> UserResponse:
    return UserResponse(
        name=user["name"],
        email=user["email"],
    )


def _build_auth_response(user: dict) -> AuthResponse:
    email = user["email"]
    return AuthResponse(
        user=_serialize_user(user),
        tokens={
            "access_token": create_access_token(email),
            "refresh_token": create_refresh_token(email),
        },
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    database: AsyncIOMotorDatabase = Depends(get_database),
) -> AuthResponse:
    user_document = {
        "name": payload.name.strip(),
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(UTC),
    }

    try:
        await database[settings.users_collection].insert_one(user_document)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from exc

    return _build_auth_response(user_document)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: UserLogin,
    database: AsyncIOMotorDatabase = Depends(get_database),
) -> AuthResponse:
    user = await database[settings.users_collection].find_one({"email": payload.email.lower()})
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    return _build_auth_response(user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    database: AsyncIOMotorDatabase = Depends(get_database),
) -> AuthResponse:
    try:
        decoded = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required.",
        )

    user = await database[settings.users_collection].find_one({"email": decoded.get("sub")})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return _build_auth_response(user)


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return _serialize_user(current_user)
