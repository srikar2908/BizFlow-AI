from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.config import Settings
from app.services.dashboard_service import DashboardService

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DOC_ID = UUID("00000000-0000-0000-0000-000000000101")
NOW = datetime(2026, 11, 5, 12, tzinfo=UTC).isoformat()


class FakeResponse:
    headers = {"content-range": "0-0/1"}

    def __init__(self, body: list[dict[str, object]], status_code: int = 200) -> None:
        self.body = body
        self.status_code = status_code

    def json(self) -> list[dict[str, object]]:
        return self.body


class FakeClient:
    calls: list[tuple[str, dict[str, object]]] = []
    activity_status = 200

    def __init__(self, *, timeout: float) -> None:
        assert timeout == 20.0

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def get(
        self, url: str, *, headers: dict[str, str], params: dict[str, str]
    ) -> FakeResponse:
        assert headers["Authorization"] == "Bearer user-token"
        assert params["user_id"] == f"eq.{USER_ID}"
        self.calls.append((url, params))
        if url.endswith("/documents"):
            return FakeResponse(
                [
                    {
                        "id": str(DOC_ID),
                        "filename": "brief.pdf",
                        "status": "completed",
                        "created_at": NOW,
                        "metadata": {"proposal_draft": {"proposal_title": "Draft"}},
                    }
                ]
            )
        if url.endswith("/workflow_runs"):
            return FakeResponse(
                [
                    {
                        "id": "00000000-0000-0000-0000-000000000201",
                        "document_id": str(DOC_ID),
                        "workflow_type": "proposal_follow_up",
                        "status": "pending",
                        "approved_by_user": False,
                        "created_at": NOW,
                        "documents": {"filename": "brief.pdf"},
                    }
                ]
            )
        if self.activity_status >= 400:
            return FakeResponse([], status_code=self.activity_status)
        return FakeResponse(
            [
                {
                    "id": "00000000-0000-0000-0000-000000000301",
                    "event_type": "proposal_generated",
                    "document_id": str(DOC_ID),
                    "occurred_at": NOW,
                    "details": {"filename": "brief.pdf"},
                }
            ]
        )

    async def head(
        self, url: str, *, headers: dict[str, str], params: dict[str, str]
    ) -> FakeResponse:
        assert headers["Authorization"] == "Bearer user-token"
        assert params["user_id"] == f"eq.{USER_ID}"
        self.calls.append((url, params))
        return FakeResponse([])


@pytest.mark.asyncio
async def test_dashboard_counts_and_recent_activity_are_user_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeClient.calls = []
    FakeClient.activity_status = 200
    monkeypatch.setattr("app.services.dashboard_service.httpx.AsyncClient", FakeClient)
    result = await DashboardService(
        Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon")
    ).get_dashboard(user_id=USER_ID, access_token="user-token")

    assert result.total_documents == 1
    assert result.processed_documents == 1
    assert result.proposals_generated == 1
    assert result.pending_approvals == 1
    assert result.documents[0].filename == "brief.pdf"
    assert result.workflows[0].document_filename == "brief.pdf"
    assert result.activity[0].filename == "brief.pdf"
    assert result.activity_available is True
    assert len(FakeClient.calls) == 12


@pytest.mark.asyncio
async def test_dashboard_core_data_loads_when_activity_migration_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeClient.calls = []
    FakeClient.activity_status = 404
    monkeypatch.setattr("app.services.dashboard_service.httpx.AsyncClient", FakeClient)
    result = await DashboardService(
        Settings(supabase_url="https://example.supabase.co", supabase_anon_key="anon")
    ).get_dashboard(user_id=USER_ID, access_token="user-token")

    assert result.total_documents == 1
    assert result.pending_approvals == 1
    assert result.activity == []
    assert result.activity_available is False
    FakeClient.activity_status = 200
