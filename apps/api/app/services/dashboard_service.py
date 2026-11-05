import logging
from typing import Any, cast
from uuid import UUID

import httpx

from app.core.config import Settings
from app.schemas.dashboard import (
    ApplicationSettingsResponse,
    DashboardActivity,
    DashboardDocument,
    DashboardResponse,
    DashboardWorkflow,
)

logger = logging.getLogger(__name__)


class DashboardServiceError(Exception):
    pass


class DashboardService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.supabase_url.rstrip("/")
        self.anon_key = settings.supabase_anon_key

    async def get_dashboard(self, *, user_id: UUID, access_token: str) -> DashboardResponse:
        if not self.base_url or not self.anon_key:
            raise DashboardServiceError("Supabase is not configured for dashboard data.")
        headers = {"apikey": self.anon_key, "Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            document_base = f"{self.base_url}/rest/v1/documents"
            workflow_base = f"{self.base_url}/rest/v1/workflow_runs"
            count_headers = {
                **headers,
                "Prefer": "count=exact",
                "Range-Unit": "items",
                "Range": "0-0",
            }
            totals = [
                await self._count(
                    client, document_base, count_headers, {"user_id": f"eq.{user_id}"}
                ),
                await self._count(
                    client,
                    document_base,
                    count_headers,
                    {"user_id": f"eq.{user_id}", "status": "in.(ready,completed)"},
                ),
                await self._count(
                    client,
                    document_base,
                    count_headers,
                    {"user_id": f"eq.{user_id}", "metadata->proposal_draft": "not.is.null"},
                ),
                await self._count(
                    client,
                    workflow_base,
                    count_headers,
                    {"user_id": f"eq.{user_id}", "status": "eq.completed"},
                ),
                await self._count(
                    client,
                    workflow_base,
                    count_headers,
                    {"user_id": f"eq.{user_id}", "status": "eq.pending"},
                ),
                await self._count(
                    client,
                    workflow_base,
                    count_headers,
                    {"user_id": f"eq.{user_id}", "status": "in.(failed,unknown)"},
                ),
                await self._count(
                    client,
                    document_base,
                    count_headers,
                    {"user_id": f"eq.{user_id}", "status": "eq.pending"},
                ),
                await self._count(
                    client,
                    document_base,
                    count_headers,
                    {"user_id": f"eq.{user_id}", "status": "in.(ingesting,processing)"},
                ),
                await self._count(
                    client,
                    document_base,
                    count_headers,
                    {"user_id": f"eq.{user_id}", "status": "eq.failed"},
                ),
            ]
            docs_response = await client.get(
                document_base,
                headers=headers,
                params={
                    "select": "id,filename,status,created_at,summary",
                    "user_id": f"eq.{user_id}",
                    "order": "created_at.desc",
                    "limit": "8",
                },
            )
            workflows_response = await client.get(
                workflow_base,
                headers=headers,
                params={
                    "select": (
                        "id,document_id,workflow_type,status,approved_by_user,created_at,"
                        "documents(filename)"
                    ),
                    "user_id": f"eq.{user_id}",
                    "order": "created_at.desc",
                    "limit": "8",
                },
            )
            activity_response = await client.get(
                f"{self.base_url}/rest/v1/activity_events",
                headers=headers,
                params={
                    "select": "id,event_type,document_id,occurred_at,details",
                    "user_id": f"eq.{user_id}",
                    "order": "occurred_at.desc",
                    "limit": "30",
                },
            )
        for response, data_name in (
            (docs_response, "recent documents"),
            (workflows_response, "recent workflows"),
        ):
            if response.status_code >= 400:
                raise DashboardServiceError(
                    f"Unable to load {data_name} from Supabase (HTTP {response.status_code}). "
                    "Check the API configuration, table grants, and row-level security policies."
                )
        activity_available = activity_response.status_code < 400
        if not activity_available:
            # The activity table is an optional additive feature. Keep core
            # overview statistics available while the migration is pending.
            logger.warning(
                "Dashboard activity feed unavailable: status_code=%s",
                activity_response.status_code,
            )
        docs = docs_response.json()
        workflows = workflows_response.json()
        events = activity_response.json() if activity_available else []
        if not all(isinstance(rows, list) for rows in (docs, workflows, events)):
            raise DashboardServiceError("Supabase returned an invalid dashboard response.")

        doc_rows = cast(list[dict[str, Any]], docs)
        workflow_rows = cast(list[dict[str, Any]], workflows)
        event_rows = cast(list[dict[str, Any]], events)
        document_models = [DashboardDocument.model_validate(row) for row in doc_rows[:8]]
        workflow_models = []
        for row in workflow_rows[:8]:
            relation = row.get("documents")
            workflow_models.append(
                DashboardWorkflow.model_validate(
                    {
                        **row,
                        "document_filename": relation.get("filename")
                        if isinstance(relation, dict)
                        else None,
                    }
                )
            )
        activities = []
        for row in event_rows:
            details = row.get("details")
            activities.append(
                DashboardActivity.model_validate(
                    {
                        **row,
                        "filename": details.get("filename") if isinstance(details, dict) else None,
                    }
                )
            )
        return DashboardResponse(
            total_documents=totals[0],
            processed_documents=totals[1],
            proposals_generated=totals[2],
            workflows_completed=totals[3],
            pending_approvals=totals[4],
            failed_or_unknown_executions=totals[5],
            document_status_counts={
                "pending": totals[6],
                "processing": totals[7],
                "failed": totals[8],
                "processed": totals[1],
            },
            documents=document_models,
            workflows=workflow_models,
            activity=activities,
            activity_available=activity_available,
        )

    @staticmethod
    async def _count(
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        filters: dict[str, str],
    ) -> int:
        response = await client.head(url, headers=headers, params={"select": "id", **filters})
        if response.status_code >= 400:
            raise DashboardServiceError(
                "Unable to load dashboard statistics from Supabase "
                f"(HTTP {response.status_code}). Check table grants and RLS policies."
            )
        content_range = response.headers.get("content-range", "")
        try:
            return int(content_range.rsplit("/", 1)[1])
        except (IndexError, ValueError) as exc:
            raise DashboardServiceError(
                "Supabase returned invalid dashboard count metadata."
            ) from exc

    def get_application_settings(
        self, *, user_id: UUID, email: str | None
    ) -> ApplicationSettingsResponse:
        return ApplicationSettingsResponse(
            user_id=user_id,
            email=email,
            upload_limit_bytes=self.settings.max_upload_bytes,
            supabase_configured=bool(
                self.settings.supabase_url and self.settings.supabase_anon_key
            ),
            ai_provider_configured=bool(self.settings.gemini_api_key),
            n8n_configured=bool(
                self.settings.n8n_workflow_webhook_url and self.settings.n8n_webhook_secret
            ),
            langfuse_configured=bool(
                self.settings.langfuse_enabled
                and self.settings.langfuse_public_key
                and self.settings.langfuse_secret_key
            ),
        )
