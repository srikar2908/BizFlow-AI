from typing import Any
from uuid import UUID

import httpx
import pytest

from app.core.config import Settings
from app.services.n8n_service import (
    N8nService,
    N8nServiceError,
    WorkflowTriggerRequest,
)

WORKFLOW_ID = UUID("00000000-0000-0000-0000-000000000201")
IDEMPOTENCY_KEY = "execution-key-123"


class FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self.payload = payload

    def json(self) -> Any:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeAsyncClient:
    def __init__(self, *, response: FakeResponse | Exception) -> None:
        self.response = response
        self.request: dict[str, Any] | None = None

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(
        self, url: str, *, headers: dict[str, str], json: dict[str, Any]
    ) -> FakeResponse:
        self.request = {"url": url, "headers": headers, "json": json}
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def trigger_request() -> WorkflowTriggerRequest:
    return WorkflowTriggerRequest(
        workflow_id=WORKFLOW_ID,
        workflow_type="proposal_follow_up",
        document_id=None,
        input_payload={"filename": "brief.pdf"},
        output_payload={"preview": {}},
        approved_by_user=True,
        idempotency_key=IDEMPOTENCY_KEY,
    )


def setup_client(
    monkeypatch: pytest.MonkeyPatch, response: FakeResponse | Exception
) -> FakeAsyncClient:
    fake_client = FakeAsyncClient(response=response)
    monkeypatch.setattr(
        "app.services.n8n_service.httpx.AsyncClient",
        lambda *, timeout: fake_client,
    )
    return fake_client


def service() -> N8nService:
    return N8nService(
        Settings(
            n8n_workflow_webhook_url="https://n8n.example/webhook/workflow",
            n8n_webhook_secret="server-secret-test-only",
            n8n_request_timeout_seconds=12.5,
        )
    )


@pytest.mark.asyncio
async def test_success_requires_explicit_contract_and_propagates_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = setup_client(
        monkeypatch,
        FakeResponse(
            200,
            {
                "workflow_id": str(WORKFLOW_ID),
                "status": "completed",
                "execution_id": "n8n-123",
                "result": {"record_id": "sheet-row-5"},
            },
        ),
    )

    result = await service().trigger_workflow(trigger_request())

    assert fake.request is not None
    assert fake.request["headers"]["Idempotency-Key"] == IDEMPOTENCY_KEY
    assert fake.request["json"]["idempotency_key"] == IDEMPOTENCY_KEY
    assert result.execution_id == "n8n-123"
    assert result.result == {"record_id": "sheet-row-5"}


@pytest.mark.asyncio
async def test_malformed_success_response_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_client(monkeypatch, FakeResponse(200, {"ok": True}))

    with pytest.raises(N8nServiceError) as exc_info:
        await service().trigger_workflow(trigger_request())

    assert exc_info.value.outcome == "unknown"


@pytest.mark.asyncio
async def test_mismatched_workflow_response_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_client(
        monkeypatch,
        FakeResponse(
            200,
            {
                "workflow_id": "00000000-0000-0000-0000-000000000999",
                "status": "completed",
                "result": {},
            },
        ),
    )

    with pytest.raises(N8nServiceError) as exc_info:
        await service().trigger_workflow(trigger_request())

    assert exc_info.value.outcome == "unknown"


@pytest.mark.asyncio
async def test_timeout_is_unknown_and_connection_failure_is_definite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_client(monkeypatch, httpx.ReadTimeout("read timed out"))
    with pytest.raises(N8nServiceError) as timeout_error:
        await service().trigger_workflow(trigger_request())
    assert timeout_error.value.outcome == "unknown"

    setup_client(monkeypatch, httpx.ConnectError("connection refused"))
    with pytest.raises(N8nServiceError) as connection_error:
        await service().trigger_workflow(trigger_request())
    assert connection_error.value.outcome == "definite_failure"


@pytest.mark.asyncio
async def test_non_2xx_is_not_reported_as_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    setup_client(monkeypatch, FakeResponse(500, {"message": "server error"}))

    with pytest.raises(N8nServiceError) as exc_info:
        await service().trigger_workflow(trigger_request())

    assert exc_info.value.outcome == "unknown"
