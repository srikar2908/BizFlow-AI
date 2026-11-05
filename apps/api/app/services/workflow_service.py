import logging
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import httpx

from app.core.config import Settings
from app.schemas.workflows import WorkflowRun, WorkflowType
from app.services.n8n_service import (
    N8nService,
    N8nServiceError,
    WorkflowTriggerRequest,
)
from app.services.observability_service import ObservabilityService

logger = logging.getLogger(__name__)


class WorkflowServiceError(Exception):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class WorkflowService:
    def __init__(
        self,
        settings: Settings,
        n8n_service: N8nService | None = None,
        observability_service: ObservabilityService | None = None,
    ) -> None:
        self.settings = settings
        self.supabase_url = settings.supabase_url.rstrip("/")
        self.supabase_anon_key = settings.supabase_anon_key
        self.n8n_service = n8n_service or N8nService(settings)
        self.observability = observability_service or ObservabilityService(settings)

    async def create_preview(
        self,
        *,
        user_id: UUID,
        access_token: str,
        document_id: UUID,
        workflow_type: WorkflowType,
    ) -> WorkflowRun:
        document = await self._get_document(
            user_id=user_id,
            access_token=access_token,
            document_id=document_id,
        )
        if document.get("status") not in {"completed", "ready"}:
            raise WorkflowServiceError(
                "Document must be completed before a workflow preview can be created.",
                status_code=400,
            )

        input_payload = self._build_input_payload(document=document, workflow_type=workflow_type)
        output_payload = self._build_output_payload(document=document, workflow_type=workflow_type)
        return await self._insert_workflow_run(
            user_id=user_id,
            access_token=access_token,
            document_id=document_id,
            workflow_type=workflow_type,
            input_payload=input_payload,
            output_payload=output_payload,
        )

    async def approve_workflow(
        self,
        *,
        user_id: UUID,
        access_token: str,
        workflow_id: UUID,
    ) -> WorkflowRun:
        # The database predicate is the transition guard. Competing requests
        # cannot both change the same pending row to approved.
        return await self._conditional_transition(
            user_id=user_id,
            access_token=access_token,
            workflow_id=workflow_id,
            expected_status="pending",
            update={
                "status": "approved",
                "approved_by_user": True,
                "approved_at": _now_iso(),
                "error_message": None,
            },
            conflict_message="Workflow is no longer pending and cannot be approved.",
        )

    async def list_workflows(
        self,
        *,
        user_id: UUID,
        access_token: str,
    ) -> list[WorkflowRun]:
        self._require_database_config(access_token)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.supabase_url}/rest/v1/workflow_runs",
                headers=self._database_headers(access_token),
                params={
                    "select": self._workflow_select(),
                    "user_id": f"eq.{user_id}",
                    "order": "created_at.desc",
                },
            )

        self._raise_for_supabase_error(response, "Unable to read workflows.")
        payload = response.json()
        if not isinstance(payload, list):
            raise WorkflowServiceError("Unexpected workflows response from Supabase.")
        return [self._workflow_from_row(row) for row in cast(list[dict[str, Any]], payload)]

    async def execute_workflow(
        self,
        *,
        user_id: UUID,
        access_token: str,
        workflow_id: UUID,
    ) -> WorkflowRun:
        workflow = await self._get_workflow_run(
            user_id=user_id,
            access_token=access_token,
            workflow_id=workflow_id,
        )
        if not workflow.approved_by_user:
            raise WorkflowServiceError(
                "Workflow must be explicitly approved before it can be executed.",
                status_code=409,
            )

        if workflow.status == "approved":
            # The key is written in the same atomic update that claims the row,
            # before any external request is sent.
            idempotency_key = workflow.idempotency_key or str(uuid4())
        elif (
            workflow.status == "failed"
            and workflow.execution_result is not None
            and workflow.execution_result.get("outcome") == "definite_failure"
            and workflow.idempotency_key
        ):
            # Only a known pre-delivery failure can be retried. Reuse the key.
            idempotency_key = workflow.idempotency_key
        elif workflow.status in {"running", "unknown"}:
            raise WorkflowServiceError(
                "Execution outcome may be unknown. Reconcile with n8n before any retry.",
                status_code=409,
            )
        else:
            raise WorkflowServiceError(
                "Only an approved workflow or a definitely undelivered execution can run.",
                status_code=409,
            )

        running = await self._conditional_transition(
            user_id=user_id,
            access_token=access_token,
            workflow_id=workflow_id,
            expected_status=workflow.status,
            expected_idempotency_key=(
                workflow.idempotency_key if workflow.status == "failed" else None
            ),
            expected_approved=True,
            update={
                "status": "running",
                "idempotency_key": idempotency_key,
                "execution_started_at": _now_iso(),
                "completed_at": None,
                "execution_result": None,
                "error_message": None,
            },
            conflict_message=(
                "Another request claimed this execution, or the workflow state changed."
            ),
        )

        try:
            with self.observability.trace(
                operation="workflow_execution",
                user_id=user_id,
                document_id=running.document_id,
                workflow_id=running.id,
                metadata={"workflow_type": running.workflow_type},
            ):
                result = await self.n8n_service.trigger_workflow(
                    WorkflowTriggerRequest(
                        workflow_id=running.id,
                        workflow_type=running.workflow_type,
                        document_id=running.document_id,
                        input_payload=running.input_payload,
                        output_payload=running.output_payload,
                        approved_by_user=running.approved_by_user,
                        idempotency_key=idempotency_key,
                    )
                )
        except N8nServiceError as exc:
            terminal_status = "failed" if exc.outcome == "definite_failure" else "unknown"
            execution_result = {
                "outcome": exc.outcome,
                "message": str(exc),
            }
            await self._conditional_transition(
                user_id=user_id,
                access_token=access_token,
                workflow_id=workflow_id,
                expected_status="running",
                expected_idempotency_key=idempotency_key,
                update={
                    "status": terminal_status,
                    "completed_at": _now_iso() if terminal_status == "failed" else None,
                    "execution_result": execution_result,
                    "error_message": str(exc),
                },
                conflict_message="Workflow state changed while recording n8n failure.",
            )
            raise WorkflowServiceError(str(exc), status_code=exc.status_code) from exc

        completed_at = _now_iso()
        return await self._conditional_transition(
            user_id=user_id,
            access_token=access_token,
            workflow_id=workflow_id,
            expected_status="running",
            expected_idempotency_key=idempotency_key,
            update={
                "status": "completed",
                "completed_at": completed_at,
                "n8n_execution_id": result.execution_id,
                "execution_result": result.result,
                "error_message": None,
            },
            conflict_message=(
                "n8n reported completion, but the workflow row changed before the result "
                "could be saved. Reconcile the execution before retrying."
            ),
        )

    async def _conditional_transition(
        self,
        *,
        user_id: UUID,
        access_token: str,
        workflow_id: UUID,
        expected_status: str,
        update: dict[str, Any],
        conflict_message: str,
        expected_approved: bool | None = None,
        expected_idempotency_key: str | None = None,
    ) -> WorkflowRun:
        self._require_database_config(access_token)
        params: dict[str, str] = {
            "id": f"eq.{workflow_id}",
            "user_id": f"eq.{user_id}",
            "status": f"eq.{expected_status}",
            "select": self._workflow_select(),
        }
        if expected_approved is not None:
            params["approved_by_user"] = f"eq.{str(expected_approved).lower()}"
        if expected_idempotency_key is not None:
            params["idempotency_key"] = f"eq.{expected_idempotency_key}"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.patch(
                f"{self.supabase_url}/rest/v1/workflow_runs",
                headers={
                    **self._database_headers(access_token),
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                params=params,
                json=update,
            )

        self._raise_for_supabase_error(response, "Unable to update workflow.")
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            raise WorkflowServiceError(conflict_message, status_code=409)
        return self._workflow_from_row(cast(dict[str, Any], payload[0]))

    async def _get_document(
        self,
        *,
        user_id: UUID,
        access_token: str,
        document_id: UUID,
    ) -> dict[str, Any]:
        self._require_database_config(access_token)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.supabase_url}/rest/v1/documents",
                headers=self._database_headers(access_token),
                params={
                    "select": "id,filename,status,summary,metadata",
                    "id": f"eq.{document_id}",
                    "user_id": f"eq.{user_id}",
                    "limit": "1",
                },
            )

        self._raise_for_supabase_error(response, "Unable to read document.")
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            raise WorkflowServiceError("Document not found.", status_code=404)
        return cast(dict[str, Any], payload[0])

    async def _get_workflow_run(
        self,
        *,
        user_id: UUID,
        access_token: str,
        workflow_id: UUID,
    ) -> WorkflowRun:
        self._require_database_config(access_token)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.supabase_url}/rest/v1/workflow_runs",
                headers=self._database_headers(access_token),
                params={
                    "select": self._workflow_select(),
                    "id": f"eq.{workflow_id}",
                    "user_id": f"eq.{user_id}",
                    "limit": "1",
                },
            )

        self._raise_for_supabase_error(response, "Unable to read workflow.")
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            raise WorkflowServiceError("Workflow not found.", status_code=404)
        return self._workflow_from_row(cast(dict[str, Any], payload[0]))

    async def _insert_workflow_run(
        self,
        *,
        user_id: UUID,
        access_token: str,
        document_id: UUID,
        workflow_type: WorkflowType,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any],
    ) -> WorkflowRun:
        self._require_database_config(access_token)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.supabase_url}/rest/v1/workflow_runs",
                headers={
                    **self._database_headers(access_token),
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                params={"select": self._workflow_select()},
                json={
                    "user_id": str(user_id),
                    "document_id": str(document_id),
                    "workflow_type": workflow_type,
                    "status": "pending",
                    "input_payload": input_payload,
                    "output_payload": output_payload,
                    "approved_by_user": False,
                },
            )

        self._raise_for_supabase_error(response, "Unable to create workflow preview.")
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            raise WorkflowServiceError("Unexpected workflow insert response from Supabase.")
        return self._workflow_from_row(cast(dict[str, Any], payload[0]))

    @staticmethod
    def _build_input_payload(
        *,
        document: dict[str, Any],
        workflow_type: WorkflowType,
    ) -> dict[str, Any]:
        metadata = document.get("metadata")
        safe_metadata = metadata if isinstance(metadata, dict) else {}
        return {
            "document_id": document.get("id"),
            "filename": document.get("filename"),
            "workflow_type": workflow_type,
            "summary": document.get("summary"),
            "recommended_actions": safe_metadata.get("recommended_actions", []),
            "proposal_draft": safe_metadata.get("proposal_draft"),
            "email_draft": safe_metadata.get("email_draft"),
        }

    @staticmethod
    def _build_output_payload(
        *,
        document: dict[str, Any],
        workflow_type: WorkflowType,
    ) -> dict[str, Any]:
        metadata = document.get("metadata")
        safe_metadata = metadata if isinstance(metadata, dict) else {}
        email_draft = safe_metadata.get("email_draft")
        proposal_draft = safe_metadata.get("proposal_draft")
        return {
            "workflow_type": workflow_type,
            "document": {
                "id": document.get("id"),
                "filename": document.get("filename"),
                "summary": document.get("summary"),
            },
            "approval_required": True,
            "approved_by_user": False,
            "preview": {
                "email_draft": email_draft if isinstance(email_draft, dict) else None,
                "proposal_draft": proposal_draft if isinstance(proposal_draft, dict) else None,
                "recommended_actions": safe_metadata.get("recommended_actions", []),
            },
            "next_step": "Review and approve before any external workflow is triggered.",
        }

    def _database_headers(self, access_token: str) -> dict[str, str]:
        if not self.supabase_anon_key or not access_token:
            raise WorkflowServiceError("Supabase workflow access is not configured.")
        return {
            "apikey": self.supabase_anon_key,
            "Authorization": f"Bearer {access_token}",
        }

    def _require_database_config(self, access_token: str) -> None:
        if not self.supabase_url or not self.supabase_anon_key or not access_token:
            raise WorkflowServiceError("Supabase workflow access is not configured.")

    @staticmethod
    def _workflow_select() -> str:
        return (
            "id,document_id,workflow_type,status,input_payload,output_payload,"
            "approved_by_user,approved_at,execution_started_at,completed_at,"
            "n8n_execution_id,idempotency_key,execution_result,error_message,"
            "created_at,updated_at,documents(filename)"
        )

    @staticmethod
    def _workflow_from_row(row: dict[str, Any]) -> WorkflowRun:
        workflow_id = row.get("id")
        workflow_type = row.get("workflow_type")
        status = row.get("status")
        created_at = row.get("created_at")
        updated_at = row.get("updated_at")
        document_id = row.get("document_id")
        documents = row.get("documents")
        document_filename = None
        if isinstance(documents, dict) and isinstance(documents.get("filename"), str):
            document_filename = documents["filename"]

        if not isinstance(workflow_id, str):
            raise WorkflowServiceError("Workflow row is missing id.")
        if workflow_type not in {"proposal_follow_up", "email_draft_review", "lead_capture"}:
            raise WorkflowServiceError("Workflow row has invalid type.")
        if status not in {
            "pending",
            "approved",
            "running",
            "completed",
            "failed",
            "unknown",
            "sent",
        }:
            raise WorkflowServiceError("Workflow row has invalid status.")
        if not isinstance(created_at, str):
            raise WorkflowServiceError("Workflow row is missing created_at.")

        input_payload = row.get("input_payload")
        output_payload = row.get("output_payload")
        approved_by_user = row.get("approved_by_user")
        error_message = row.get("error_message")
        execution_result = row.get("execution_result")

        return WorkflowRun(
            id=UUID(workflow_id),
            document_id=UUID(document_id) if isinstance(document_id, str) else None,
            document_filename=document_filename,
            workflow_type=workflow_type,
            status=status,
            input_payload=input_payload if isinstance(input_payload, dict) else {},
            output_payload=output_payload if isinstance(output_payload, dict) else {},
            approved_by_user=approved_by_user if isinstance(approved_by_user, bool) else False,
            approved_at=_parse_datetime(row.get("approved_at")),
            execution_started_at=_parse_datetime(row.get("execution_started_at")),
            completed_at=_parse_datetime(row.get("completed_at")),
            n8n_execution_id=(
                row.get("n8n_execution_id")
                if isinstance(row.get("n8n_execution_id"), str)
                else None
            ),
            idempotency_key=(
                row.get("idempotency_key") if isinstance(row.get("idempotency_key"), str) else None
            ),
            execution_result=execution_result if isinstance(execution_result, dict) else None,
            error_message=error_message if isinstance(error_message, str) else None,
            created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00")),
            updated_at=_parse_datetime(updated_at),
        )

    @staticmethod
    def _raise_for_supabase_error(response: httpx.Response, message: str) -> None:
        if response.status_code >= 400:
            # PostgREST reports unknown/missing columns as a client error. Keep
            # details out of logs and make the schema prerequisite explicit.
            if response.status_code == 400:
                raise WorkflowServiceError(
                    "Workflow database schema is incompatible. Review and apply migration "
                    "0002 before deploying this workflow implementation.",
                    status_code=503,
                )
            logger.warning(
                "Supabase workflow REST error: status_code=%s path=%s",
                response.status_code,
                response.request.url.path,
            )
            raise WorkflowServiceError(message, status_code=502)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
