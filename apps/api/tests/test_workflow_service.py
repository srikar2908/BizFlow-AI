import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import pytest

from app.core.config import Settings
from app.schemas.workflows import WorkflowRun
from app.services.n8n_service import N8nServiceError, WorkflowTriggerRequest, WorkflowTriggerResult
from app.services.workflow_service import WorkflowService, WorkflowServiceError
from tests.test_workflows import USER_ID, WORKFLOW_ID, workflow_run

CREATED_AT = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)


class FakeN8nService:
    def __init__(self, *, errors: list[N8nServiceError] | None = None) -> None:
        self.errors = list(errors or [])
        self.requests: list[WorkflowTriggerRequest] = []

    async def trigger_workflow(self, request: WorkflowTriggerRequest) -> WorkflowTriggerResult:
        self.requests.append(request)
        if self.errors:
            raise self.errors.pop(0)
        return WorkflowTriggerResult(
            workflow_id=request.workflow_id,
            status="completed",
            execution_id="n8n-exec-123",
            result={"sheets_row_id": "row-7"},
        )


class FakeWorkflowService(WorkflowService):
    """Models a conditional database UPDATE; no network or database is contacted."""

    def __init__(
        self,
        *,
        workflow: WorkflowRun,
        errors: list[N8nServiceError] | None = None,
    ) -> None:
        self.fake_n8n_service = FakeN8nService(errors=errors)
        super().__init__(
            Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon"),
            n8n_service=self.fake_n8n_service,  # type: ignore[arg-type]
        )
        self.workflow = workflow
        self.claim_attempts: list[tuple[str, str | None]] = []
        self._lock = asyncio.Lock()

    async def _get_workflow_run(
        self,
        *,
        user_id: UUID,
        access_token: str,
        workflow_id: UUID,
    ) -> WorkflowRun:
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        assert workflow_id == WORKFLOW_ID
        return self.workflow

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
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        assert workflow_id == WORKFLOW_ID
        async with self._lock:
            self.claim_attempts.append((expected_status, update.get("idempotency_key")))
            if self.workflow.status != expected_status:
                raise WorkflowServiceError(conflict_message, status_code=409)
            if (
                expected_approved is not None
                and self.workflow.approved_by_user != expected_approved
            ):
                raise WorkflowServiceError(conflict_message, status_code=409)
            if (
                expected_idempotency_key is not None
                and self.workflow.idempotency_key != expected_idempotency_key
            ):
                raise WorkflowServiceError(conflict_message, status_code=409)

            fields = self.workflow.model_dump()
            fields.update(update)
            self.workflow = WorkflowRun(**fields)
            return self.workflow


@pytest.mark.asyncio
async def test_pending_workflow_cannot_execute() -> None:
    service = FakeWorkflowService(workflow=workflow_run(status="pending", approved=False))

    with pytest.raises(WorkflowServiceError) as exc_info:
        await service.execute_workflow(
            user_id=USER_ID,
            access_token="test-access-token",
            workflow_id=WORKFLOW_ID,
        )

    assert exc_info.value.status_code == 409
    assert service.fake_n8n_service.requests == []


@pytest.mark.asyncio
async def test_approved_but_not_explicitly_approved_workflow_cannot_execute() -> None:
    service = FakeWorkflowService(workflow=workflow_run(status="approved", approved=False))

    with pytest.raises(WorkflowServiceError):
        await service.execute_workflow(
            user_id=USER_ID,
            access_token="test-access-token",
            workflow_id=WORKFLOW_ID,
        )

    assert service.fake_n8n_service.requests == []
    assert service.workflow.status == "approved"


@pytest.mark.asyncio
async def test_approval_is_single_conditional_transition() -> None:
    service = FakeWorkflowService(workflow=workflow_run(status="pending", approved=False))
    results = await asyncio.gather(
        *(
            service.approve_workflow(
                user_id=USER_ID,
                access_token="test-access-token",
                workflow_id=WORKFLOW_ID,
            )
            for _ in range(2)
        ),
        return_exceptions=True,
    )

    assert sum(isinstance(result, WorkflowRun) for result in results) == 1
    assert sum(isinstance(result, WorkflowServiceError) for result in results) == 1
    assert service.workflow.status == "approved"
    assert service.workflow.approved_by_user is True
    assert service.workflow.approved_at is not None


@pytest.mark.asyncio
async def test_concurrent_execution_claim_calls_n8n_once() -> None:
    service = FakeWorkflowService(workflow=workflow_run(status="approved", approved=True))
    results = await asyncio.gather(
        *(
            service.execute_workflow(
                user_id=USER_ID,
                access_token="test-access-token",
                workflow_id=WORKFLOW_ID,
            )
            for _ in range(2)
        ),
        return_exceptions=True,
    )

    assert sum(isinstance(result, WorkflowRun) for result in results) == 1
    assert sum(isinstance(result, WorkflowServiceError) for result in results) == 1
    assert len(service.fake_n8n_service.requests) == 1
    assert service.workflow.status == "completed"


@pytest.mark.asyncio
async def test_success_persists_normalized_result_and_execution_metadata() -> None:
    service = FakeWorkflowService(workflow=workflow_run(status="approved", approved=True))

    result = await service.execute_workflow(
        user_id=USER_ID,
        access_token="test-access-token",
        workflow_id=WORKFLOW_ID,
    )

    assert result.status == "completed"
    assert result.idempotency_key
    assert result.execution_started_at is not None
    assert result.completed_at is not None
    assert result.n8n_execution_id == "n8n-exec-123"
    assert result.execution_result == {"sheets_row_id": "row-7"}
    assert service.fake_n8n_service.requests[0].idempotency_key == result.idempotency_key


@pytest.mark.asyncio
async def test_definite_failure_can_retry_with_original_idempotency_key() -> None:
    service = FakeWorkflowService(
        workflow=workflow_run(status="approved", approved=True),
        errors=[
            N8nServiceError(
                "Unable to connect to n8n; execution was not delivered.",
                outcome="definite_failure",
            )
        ],
    )

    with pytest.raises(WorkflowServiceError):
        await service.execute_workflow(
            user_id=USER_ID,
            access_token="test-access-token",
            workflow_id=WORKFLOW_ID,
        )
    original_key = service.workflow.idempotency_key
    assert service.workflow.status == "failed"
    assert original_key

    result = await service.execute_workflow(
        user_id=USER_ID,
        access_token="test-access-token",
        workflow_id=WORKFLOW_ID,
    )

    assert result.status == "completed"
    assert [request.idempotency_key for request in service.fake_n8n_service.requests] == [
        original_key,
        original_key,
    ]


@pytest.mark.asyncio
async def test_ambiguous_timeout_becomes_unknown_and_cannot_retry() -> None:
    service = FakeWorkflowService(
        workflow=workflow_run(status="approved", approved=True),
        errors=[N8nServiceError("n8n response timed out; outcome unknown.", outcome="unknown")],
    )

    with pytest.raises(WorkflowServiceError):
        await service.execute_workflow(
            user_id=USER_ID,
            access_token="test-access-token",
            workflow_id=WORKFLOW_ID,
        )

    original_key = service.workflow.idempotency_key
    assert service.workflow.status == "unknown"
    assert service.workflow.execution_result == {
        "outcome": "unknown",
        "message": "n8n response timed out; outcome unknown.",
    }
    with pytest.raises(WorkflowServiceError) as exc_info:
        await service.execute_workflow(
            user_id=USER_ID,
            access_token="test-access-token",
            workflow_id=WORKFLOW_ID,
        )
    assert exc_info.value.status_code == 409
    assert len(service.fake_n8n_service.requests) == 1
    assert service.workflow.idempotency_key == original_key


@pytest.mark.asyncio
async def test_legacy_failed_workflow_without_known_outcome_is_not_retried() -> None:
    legacy = workflow_run(status="failed", approved=True)
    service = FakeWorkflowService(workflow=legacy)
    with pytest.raises(WorkflowServiceError):
        await service.execute_workflow(
            user_id=USER_ID,
            access_token="test-access-token",
            workflow_id=WORKFLOW_ID,
        )
    assert service.fake_n8n_service.requests == []


class FakeRestClient:
    def __init__(self, *, response: httpx.Response) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> "FakeRestClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append({"url": url, **kwargs})
        return self.response


@pytest.mark.asyncio
async def test_approval_uses_owner_and_pending_predicates_in_single_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = workflow_run(status="approved", approved=True).model_dump(mode="json")
    row.update(
        {
            "approved_at": "2026-11-05T12:00:00Z",
            "execution_started_at": None,
            "completed_at": None,
            "n8n_execution_id": None,
            "idempotency_key": None,
            "execution_result": None,
            "documents": {"filename": "proposal.pdf"},
        }
    )
    response = httpx.Response(200, json=[row], request=httpx.Request("PATCH", "https://db.test"))
    fake_client = FakeRestClient(response=response)
    monkeypatch.setattr(
        "app.services.workflow_service.httpx.AsyncClient",
        lambda *, timeout: fake_client,
    )
    service = WorkflowService(Settings(supabase_url="https://db.test", supabase_anon_key="anon"))

    await service.approve_workflow(
        user_id=USER_ID,
        access_token="access",
        workflow_id=WORKFLOW_ID,
    )

    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["params"]["id"] == f"eq.{WORKFLOW_ID}"
    assert call["params"]["user_id"] == f"eq.{USER_ID}"
    assert call["params"]["status"] == "eq.pending"
    assert call["json"]["status"] == "approved"
    assert call["json"]["approved_by_user"] is True
    assert call["json"]["approved_at"]


@pytest.mark.asyncio
async def test_execution_claim_is_owner_approved_and_status_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = workflow_run(status="approved", approved=True).model_dump(mode="json")
    row.update(
        {
            "approved_at": "2026-11-05T12:00:00Z",
            "execution_started_at": "2026-11-05T12:01:00Z",
            "completed_at": None,
            "n8n_execution_id": None,
            "idempotency_key": "stable-execution-key",
            "execution_result": None,
            "documents": {"filename": "proposal.pdf"},
        }
    )
    response = httpx.Response(200, json=[row], request=httpx.Request("PATCH", "https://db.test"))
    fake_client = FakeRestClient(response=response)
    monkeypatch.setattr(
        "app.services.workflow_service.httpx.AsyncClient",
        lambda *, timeout: fake_client,
    )
    service = WorkflowService(Settings(supabase_url="https://db.test", supabase_anon_key="anon"))

    await service._conditional_transition(
        user_id=USER_ID,
        access_token="access",
        workflow_id=WORKFLOW_ID,
        expected_status="approved",
        expected_approved=True,
        update={
            "status": "running",
            "idempotency_key": "stable-execution-key",
            "execution_started_at": "2026-11-05T12:01:00Z",
        },
        conflict_message="claim lost",
    )

    call = fake_client.calls[0]
    assert call["params"]["id"] == f"eq.{WORKFLOW_ID}"
    assert call["params"]["user_id"] == f"eq.{USER_ID}"
    assert call["params"]["status"] == "eq.approved"
    assert call["params"]["approved_by_user"] == "eq.true"
    assert call["json"]["status"] == "running"
    assert call["json"]["idempotency_key"] == "stable-execution-key"
