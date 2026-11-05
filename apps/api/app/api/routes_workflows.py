from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.schemas.workflows import (
    WorkflowApprovalResponse,
    WorkflowPreviewRequest,
    WorkflowPreviewResponse,
    WorkflowRun,
)
from app.services.workflow_service import WorkflowService, WorkflowServiceError

router = APIRouter(prefix="/workflows", tags=["workflows"])


def get_workflow_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkflowService:
    return WorkflowService(settings)


@router.post("/preview", response_model=WorkflowPreviewResponse)
async def create_workflow_preview(
    payload: WorkflowPreviewRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> WorkflowRun:
    try:
        return await service.create_preview(
            user_id=current_user.id,
            access_token=current_user.access_token,
            document_id=payload.document_id,
            workflow_type=payload.workflow_type,
        )
    except WorkflowServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{workflow_id}/approve", response_model=WorkflowApprovalResponse)
async def approve_workflow(
    workflow_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> WorkflowRun:
    try:
        return await service.approve_workflow(
            user_id=current_user.id,
            access_token=current_user.access_token,
            workflow_id=workflow_id,
        )
    except WorkflowServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{workflow_id}/execute", response_model=WorkflowRun)
async def execute_workflow(
    workflow_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> WorkflowRun:
    try:
        return await service.execute_workflow(
            user_id=current_user.id,
            access_token=current_user.access_token,
            workflow_id=workflow_id,
        )
    except WorkflowServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("", response_model=list[WorkflowRun])
async def list_workflows(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> list[WorkflowRun]:
    try:
        return await service.list_workflows(
            user_id=current_user.id,
            access_token=current_user.access_token,
        )
    except WorkflowServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
