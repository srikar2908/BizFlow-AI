from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

WorkflowType = Literal["proposal_follow_up", "email_draft_review", "lead_capture"]
WorkflowStatus = Literal["pending", "approved", "running", "completed", "failed", "unknown", "sent"]


class WorkflowPreviewRequest(BaseModel):
    document_id: UUID
    workflow_type: WorkflowType


class WorkflowRun(BaseModel):
    id: UUID
    document_id: UUID | None
    document_filename: str | None = None
    workflow_type: WorkflowType
    status: WorkflowStatus
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    approved_by_user: bool
    approved_at: datetime | None = None
    execution_started_at: datetime | None = None
    completed_at: datetime | None = None
    n8n_execution_id: str | None = None
    idempotency_key: str | None = None
    execution_result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class WorkflowPreviewResponse(WorkflowRun):
    pass


class WorkflowApprovalResponse(WorkflowRun):
    pass
