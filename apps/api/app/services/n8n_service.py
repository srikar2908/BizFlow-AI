from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings, get_settings

ExecutionOutcome = Literal["definite_failure", "unknown"]


@dataclass(frozen=True)
class WorkflowTriggerRequest:
    workflow_id: UUID
    workflow_type: str
    document_id: UUID | None
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    approved_by_user: bool
    idempotency_key: str


@dataclass(frozen=True)
class WorkflowTriggerResult:
    workflow_id: UUID
    status: Literal["completed"]
    execution_id: str | None
    result: dict[str, Any]


class N8nWebhookResponse(BaseModel):
    """Synchronous completion response required from the configured webhook."""

    model_config = ConfigDict(extra="forbid")

    workflow_id: UUID
    status: Literal["completed"]
    execution_id: str | None = Field(default=None, min_length=1, max_length=200)
    result: dict[str, Any]


class N8nServiceError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        outcome: ExecutionOutcome = "unknown",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.outcome = outcome


class N8nService:
    """Single boundary for authenticated n8n webhook calls."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.webhook_url = self.settings.n8n_workflow_webhook_url
        self.webhook_secret = self.settings.n8n_webhook_secret
        self.timeout_seconds = self.settings.n8n_request_timeout_seconds

    async def trigger_workflow(self, request: WorkflowTriggerRequest) -> WorkflowTriggerResult:
        if not self.webhook_url:
            raise N8nServiceError(
                "N8N_WORKFLOW_WEBHOOK_URL is not configured.", outcome="definite_failure"
            )
        if not self.webhook_secret:
            raise N8nServiceError(
                "N8N_WEBHOOK_SECRET is not configured.", outcome="definite_failure"
            )
        if not request.approved_by_user:
            raise N8nServiceError(
                "Workflow must be approved before execution.",
                status_code=400,
                outcome="definite_failure",
            )
        if not request.idempotency_key:
            raise N8nServiceError(
                "Workflow idempotency key is missing.", outcome="definite_failure"
            )

        payload = {
            "workflow_id": str(request.workflow_id),
            "workflow_type": request.workflow_type,
            "document_id": str(request.document_id) if request.document_id is not None else None,
            "input_payload": request.input_payload,
            "output_payload": request.output_payload,
            "approved_by_user": request.approved_by_user,
            "idempotency_key": request.idempotency_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.webhook_url,
                    headers={
                        "X-BizFlow-Webhook-Secret": self.webhook_secret,
                        "Idempotency-Key": request.idempotency_key,
                    },
                    json=payload,
                )
        except httpx.ConnectError as exc:
            # No connection was established, so the request was not delivered.
            raise N8nServiceError(
                "Unable to connect to n8n; execution was not delivered.",
                outcome="definite_failure",
            ) from exc
        except httpx.TimeoutException as exc:
            # The server may have accepted the request before the client timed out.
            raise N8nServiceError(
                "n8n response timed out; execution outcome is unknown. Do not retry automatically.",
                outcome="unknown",
            ) from exc
        except httpx.HTTPError as exc:
            raise N8nServiceError(
                "n8n connection failed; execution outcome is unknown.", outcome="unknown"
            ) from exc

        if response.status_code < 200 or response.status_code >= 300:
            # A non-success response does not establish whether the n8n workflow
            # performed a side effect before producing the response.
            raise N8nServiceError(
                f"n8n returned HTTP {response.status_code}; execution outcome is unknown.",
                outcome="unknown",
            )

        try:
            parsed = N8nWebhookResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            # A malformed success response may follow a completed side effect.
            raise N8nServiceError(
                "n8n returned an invalid completion response; execution outcome is unknown.",
                outcome="unknown",
            ) from exc

        if parsed.workflow_id != request.workflow_id:
            raise N8nServiceError(
                "n8n response workflow_id did not match the requested workflow; "
                "execution outcome is unknown.",
                outcome="unknown",
            )

        return WorkflowTriggerResult(
            workflow_id=parsed.workflow_id,
            status=parsed.status,
            execution_id=parsed.execution_id,
            result=parsed.result,
        )
