from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas.user import UpdateUserLevelRequest
from app.services.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
)

router = APIRouter(
    prefix="/user",
    tags=["user"]
)


@router.post("/update_level", status_code=status.HTTP_200_OK)
async def update_user_level(
    request: UpdateUserLevelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates the user's proficiency level and generates a new access token."""
    if current_user.id == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest user cannot update level."
        )

    valid_levels = ["A1", "A2", "B1", "B2"]
    if request.level not in valid_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid level. Must be one of {valid_levels}"
        )

    current_user.current_level = request.level
    try:
        await db.commit()
        await db.refresh(current_user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user level: {e}"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": current_user.email, "current_level": current_user.current_level},
        expires_delta=access_token_expires
    )

    return {
        "message": f"User level updated to {current_user.current_level}",
        "new_token": new_access_token
    }
