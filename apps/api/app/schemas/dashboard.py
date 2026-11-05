from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DashboardDocument(BaseModel):
    id: UUID
    filename: str
    status: str
    created_at: datetime
    summary: str | None = None


class DashboardWorkflow(BaseModel):
    id: UUID
    document_id: UUID | None = None
    document_filename: str | None = None
    workflow_type: str
    status: str
    approved_by_user: bool
    created_at: datetime
    updated_at: datetime | None = None
    approved_at: datetime | None = None
    execution_started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class DashboardActivity(BaseModel):
    id: UUID
    event_type: str
    filename: str | None = None
    document_id: UUID | None = None
    occurred_at: datetime


class DashboardResponse(BaseModel):
    total_documents: int
    processed_documents: int
    proposals_generated: int
    workflows_completed: int
    pending_approvals: int
    failed_or_unknown_executions: int
    document_status_counts: dict[str, int]
    documents: list[DashboardDocument]
    workflows: list[DashboardWorkflow]
    activity: list[DashboardActivity]
    activity_available: bool = True


class ApplicationSettingsResponse(BaseModel):
    user_id: UUID
    email: str | None
    upload_limit_bytes: int
    supabase_configured: bool
    ai_provider_configured: bool
    n8n_configured: bool
    langfuse_configured: bool
