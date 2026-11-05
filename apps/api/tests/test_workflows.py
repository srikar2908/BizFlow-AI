from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.routes_workflows import get_workflow_service
from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.schemas.workflows import WorkflowRun, WorkflowType
from app.services.workflow_service import WorkflowServiceError

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000101")
WORKFLOW_ID = UUID("00000000-0000-0000-0000-000000000201")
CREATED_AT = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)


def workflow_run(*, status: str = "pending", approved: bool = False) -> WorkflowRun:
    return WorkflowRun(
        id=WORKFLOW_ID,
        document_id=DOCUMENT_ID,
        document_filename="proposal.pdf",
        workflow_type="proposal_follow_up",
        status=status,  # type: ignore[arg-type]
        input_payload={
            "document_id": str(DOCUMENT_ID),
            "workflow_type": "proposal_follow_up",
        },
        output_payload={
            "approval_required": True,
            "preview": {
                "email_draft": {
                    "subject": "Proposal Follow-Up for Acme",
                    "body": "Hi Acme team.",
                }
            },
        },
        approved_by_user=approved,
        error_message=None,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


class FakeWorkflowService:
    def __init__(self, *, error: WorkflowServiceError | None = None) -> None:
        self.error = error

    async def create_preview(
        self,
        *,
        user_id: UUID,
        access_token: str,
        document_id: UUID,
        workflow_type: WorkflowType,
    ) -> WorkflowRun:
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        assert document_id == DOCUMENT_ID
        assert workflow_type == "proposal_follow_up"
        if self.error is not None:
            raise self.error
        return workflow_run()

    async def approve_workflow(
        self,
        *,
        user_id: UUID,
        access_token: str,
        workflow_id: UUID,
    ) -> WorkflowRun:
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        assert workflow_id == WORKFLOW_ID
        if self.error is not None:
            raise self.error
        return workflow_run(status="approved", approved=True)

    async def list_workflows(
        self,
        *,
        user_id: UUID,
        access_token: str,
    ) -> list[WorkflowRun]:
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        if self.error is not None:
            raise self.error
        return [workflow_run()]

    async def execute_workflow(
        self,
        *,
        user_id: UUID,
        access_token: str,
        workflow_id: UUID,
    ) -> WorkflowRun:
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        assert workflow_id == WORKFLOW_ID
        if self.error is not None:
            raise self.error
        return workflow_run(status="completed", approved=True)


def override_user() -> CurrentUser:
    return CurrentUser(
        id=USER_ID,
        email="owner@example.com",
        access_token="test-access-token",
    )


def override_settings() -> Settings:
    return Settings(
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon",
    )


def setup_overrides(*, service: FakeWorkflowService | None = None) -> None:
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_workflow_service] = lambda: service or FakeWorkflowService()


def test_workflow_preview_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post(
        "/workflows/preview",
        json={"document_id": str(DOCUMENT_ID), "workflow_type": "proposal_follow_up"},
    )

    assert response.status_code == 401


def test_workflow_approve_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post(f"/workflows/{WORKFLOW_ID}/approve")

    assert response.status_code == 401


def test_workflow_list_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.get("/workflows")

    assert response.status_code == 401


def test_workflow_execute_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post(f"/workflows/{WORKFLOW_ID}/execute")

    assert response.status_code == 401


def test_workflow_preview_creates_pending_run() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.post(
            "/workflows/preview",
            json={"document_id": str(DOCUMENT_ID), "workflow_type": "proposal_follow_up"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(WORKFLOW_ID)
    assert payload["status"] == "pending"
    assert payload["approved_by_user"] is False
    assert payload["workflow_type"] == "proposal_follow_up"


def test_workflow_approve_updates_status() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.post(f"/workflows/{WORKFLOW_ID}/approve")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["approved_by_user"] is True


def test_workflow_approve_hides_other_users_workflow() -> None:
    setup_overrides(
        service=FakeWorkflowService(
            error=WorkflowServiceError("Workflow not found.", status_code=404)
        )
    )
    client = TestClient(app)

    try:
        response = client.post(f"/workflows/{WORKFLOW_ID}/approve")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_workflow_execute_hides_other_users_workflow() -> None:
    setup_overrides(
        service=FakeWorkflowService(
            error=WorkflowServiceError("Workflow not found.", status_code=404)
        )
    )
    client = TestClient(app)

    try:
        response = client.post(f"/workflows/{WORKFLOW_ID}/execute")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_pending_workflow_cannot_execute() -> None:
    setup_overrides(
        service=FakeWorkflowService(
            error=WorkflowServiceError(
                "Workflow must be approved before it can be executed.",
                status_code=400,
            )
        )
    )
    client = TestClient(app)

    try:
        response = client.post(f"/workflows/{WORKFLOW_ID}/execute")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400


def test_approved_workflow_executes_successfully() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.post(f"/workflows/{WORKFLOW_ID}/execute")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["approved_by_user"] is True


def test_workflow_list_returns_current_user_workflows() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.get("/workflows")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(WORKFLOW_ID)
    assert response.json()[0]["document_filename"] == "proposal.pdf"
