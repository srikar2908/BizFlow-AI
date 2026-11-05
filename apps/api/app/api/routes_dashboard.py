from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.schemas.dashboard import ApplicationSettingsResponse, DashboardResponse
from app.services.dashboard_service import DashboardService, DashboardServiceError

router = APIRouter(tags=["workspace"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DashboardResponse:
    try:
        return await DashboardService(settings).get_dashboard(
            user_id=user.id, access_token=user.access_token
        )
    except DashboardServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/settings", response_model=ApplicationSettingsResponse)
async def get_application_settings(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ApplicationSettingsResponse:
    return DashboardService(settings).get_application_settings(user_id=user.id, email=user.email)
