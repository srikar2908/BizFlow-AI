from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.schemas.auth import CurrentUserResponse

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(user_id=current_user.id, email=current_user.email)
