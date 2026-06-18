from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.models.auth import UserResponse


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        name=current_user["name"],
        email=current_user["email"],
    )
