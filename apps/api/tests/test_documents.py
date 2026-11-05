from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.routes_documents import (
    get_document_service,
    get_email_draft_service,
    get_ingestion_service,
    get_metadata_service,
    get_proposal_service,
    get_summary_service,
)
from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.schemas.documents import (
    DocumentEmailDraftResponse,
    DocumentMetadata,
    DocumentMetadataResponse,
    DocumentProposalResponse,
    DocumentSummary,
    DocumentSummaryGeneration,
    DocumentSummaryResponse,
    DocumentUploadResponse,
    EmailDraft,
    ProposalDraft,
)
from app.services.document_email_draft_service import DocumentEmailDraftServiceError
from app.services.document_metadata_service import DocumentMetadataServiceError
from app.services.document_proposal_service import DocumentProposalServiceError
from app.services.document_service import DocumentService
from app.services.document_summary_service import DocumentSummaryServiceError
from app.services.ingestion_service import IngestionResult, IngestionServiceError

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000101")
CREATED_AT = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)


class FakeDocumentService:
    def __init__(self, *, duplicate: bool = False) -> None:
        self.duplicate = duplicate

    async def list_documents_for_user(
        self,
        *,
        user_id: UUID,
        access_token: str,
    ) -> list[DocumentSummary]:
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        return [
            DocumentSummary(
                id=DOCUMENT_ID,
                filename="proposal.pdf",
                status="pending",
                created_at=CREATED_AT,
            )
        ]

    async def upload_document(
        self,
        *,
        user_id: UUID,
        access_token: str,
        filename: str,
        mime_type: str | None,
        content: bytes,
    ) -> DocumentUploadResponse:
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        assert filename == "proposal.pdf"
        assert mime_type == "application/pdf"
        assert content == b"same file"
        return DocumentUploadResponse(
            id=DOCUMENT_ID,
            filename=filename,
            status="pending",
            duplicate=self.duplicate,
            created_at=CREATED_AT,
        )


class FakeIngestionService:
    def __init__(self, *, error: IngestionServiceError | None = None) -> None:
        self.error = error

    async def ingest_document(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> IngestionResult:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        if self.error is not None:
            raise self.error
        return IngestionResult(document_id=document_id, status="completed", chunks_created=2)


class FakeMetadataService:
    def __init__(self, *, error: DocumentMetadataServiceError | None = None) -> None:
        self.error = error

    async def extract_metadata(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> DocumentMetadataResponse:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        if self.error is not None:
            raise self.error
        metadata = DocumentMetadata(
            document_type="proposal",
            title="Acme Proposal",
            summary="A short proposal for Acme.",
            entities=["Acme"],
            key_points=["Implementation is planned."],
            missing_information=[],
            recommended_actions=["Review scope."],
            recommended_workflow="proposal_review",
            confidence=0.84,
        )
        return DocumentMetadataResponse(
            id=document_id,
            filename="proposal.pdf",
            summary=metadata.summary,
            metadata=metadata,
        )


class FakeSummaryService:
    def __init__(self, *, error: DocumentSummaryServiceError | None = None) -> None:
        self.error = error

    async def generate_summary(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> DocumentSummaryResponse:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        if self.error is not None:
            raise self.error
        generated = DocumentSummaryGeneration(
            concise_summary="Short summary.",
            detailed_summary="Detailed summary.",
            key_points=["A key point"],
            recommended_actions=["Review next step"],
            suggested_workflow="proposal_review",
        )
        return DocumentSummaryResponse(
            id=document_id,
            filename="proposal.pdf",
            summary=generated.concise_summary,
            metadata={
                "existing_field": "kept",
                "key_points": generated.key_points,
                "recommended_actions": generated.recommended_actions,
                "suggested_workflow": generated.suggested_workflow,
                "detailed_summary": generated.detailed_summary,
            },
            generated=generated,
        )


class FakeProposalService:
    def __init__(self, *, error: DocumentProposalServiceError | None = None) -> None:
        self.error = error

    async def generate_proposal(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> DocumentProposalResponse:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        if self.error is not None:
            raise self.error
        proposal = ProposalDraft(
            proposal_title="Acme Implementation Proposal",
            executive_summary="A proposal for Acme.",
            client_problem="Acme needs implementation support.",
            proposed_solution="Deliver BizFlow AI implementation support.",
            scope_of_work=["Discovery", "Implementation"],
            deliverables=["Configured workspace"],
            timeline=[],
            assumptions=["Acme provides stakeholders."],
            missing_information=["Budget"],
            next_steps=["Confirm scope"],
        )
        return DocumentProposalResponse(
            id=document_id,
            filename="proposal.pdf",
            proposal=proposal,
            metadata={"proposal_draft": proposal.model_dump(mode="json")},
        )


class FakeEmailDraftService:
    def __init__(self, *, error: DocumentEmailDraftServiceError | None = None) -> None:
        self.error = error

    async def generate_email_draft(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> DocumentEmailDraftResponse:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        if self.error is not None:
            raise self.error
        email_draft = EmailDraft(
            subject="Proposal Follow-Up for Acme",
            body="Hi Acme team,\n\nThank you for sharing your brief.",
            purpose="proposal_follow_up",
            recipient_context="Client stakeholder",
            missing_information_questions=["What timeline should we plan around?"],
            call_to_action="Please confirm the preferred implementation timeline.",
        )
        return DocumentEmailDraftResponse(
            id=document_id,
            filename="proposal.pdf",
            email_draft=email_draft,
            metadata={"email_draft": email_draft.model_dump(mode="json")},
        )


def override_user() -> CurrentUser:
    return CurrentUser(
        id=USER_ID,
        email="owner@example.com",
        access_token="test-access-token",
    )


def override_settings(max_upload_bytes: int = 20 * 1024 * 1024) -> Settings:
    return Settings(
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon",
        supabase_service_role_key="service-role",
        max_upload_bytes=max_upload_bytes,
    )


def setup_overrides(
    *,
    service: FakeDocumentService | None = None,
    ingestion_service: FakeIngestionService | None = None,
    metadata_service: FakeMetadataService | None = None,
    summary_service: FakeSummaryService | None = None,
    proposal_service: FakeProposalService | None = None,
    email_draft_service: FakeEmailDraftService | None = None,
    max_upload_bytes: int = 20 * 1024 * 1024,
) -> None:
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_settings] = lambda: override_settings(max_upload_bytes)
    app.dependency_overrides[get_document_service] = lambda: service or FakeDocumentService()
    app.dependency_overrides[get_ingestion_service] = lambda: (
        ingestion_service or FakeIngestionService()
    )
    app.dependency_overrides[get_metadata_service] = lambda: (
        metadata_service or FakeMetadataService()
    )
    app.dependency_overrides[get_summary_service] = lambda: summary_service or FakeSummaryService()
    app.dependency_overrides[get_proposal_service] = lambda: (
        proposal_service or FakeProposalService()
    )
    app.dependency_overrides[get_email_draft_service] = lambda: (
        email_draft_service or FakeEmailDraftService()
    )


def test_documents_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.get("/documents")

    assert response.status_code == 401


def test_document_upload_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={"file": ("proposal.pdf", b"same file", "application/pdf")},
    )

    assert response.status_code == 401


def test_document_upload_rejects_invalid_file_type() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.post(
            "/documents/upload",
            files={"file": ("malware.exe", b"same file", "application/octet-stream")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400


def test_document_upload_rejects_oversized_file() -> None:
    setup_overrides(max_upload_bytes=4)
    client = TestClient(app)

    try:
        response = client.post(
            "/documents/upload",
            files={"file": ("proposal.pdf", b"same file", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 413


def test_document_upload_handles_duplicate() -> None:
    setup_overrides(service=FakeDocumentService(duplicate=True))
    client = TestClient(app)

    try:
        response = client.post(
            "/documents/upload",
            files={"file": ("proposal.pdf", b"same file", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["duplicate"] is True
    assert response.json()["filename"] == "proposal.pdf"


def test_documents_returns_current_user_documents() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.get("/documents")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(DOCUMENT_ID),
            "filename": "proposal.pdf",
            "status": "pending",
            "created_at": CREATED_AT.isoformat().replace("+00:00", "Z"),
        }
    ]


def test_document_summary_allows_empty_metadata_and_null_summary() -> None:
    summary = DocumentService._summary_from_row(
        {
            "id": str(DOCUMENT_ID),
            "filename": "proposal.pdf",
            "status": "completed",
            "created_at": CREATED_AT.isoformat().replace("+00:00", "Z"),
            "summary": None,
            "metadata": {},
        }
    )

    assert summary.summary is None
    assert summary.metadata is None


def test_document_summary_allows_partial_metadata() -> None:
    summary = DocumentService._summary_from_row(
        {
            "id": str(DOCUMENT_ID),
            "filename": "proposal.pdf",
            "status": "failed",
            "created_at": CREATED_AT.isoformat().replace("+00:00", "Z"),
            "summary": None,
            "metadata": {"ingestion_error": "Unable to extract text."},
        }
    )

    assert summary.metadata == {"ingestion_error": "Unable to extract text."}


def test_document_ingest_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post(f"/documents/{DOCUMENT_ID}/ingest")

    assert response.status_code == 401


def test_document_ingest_returns_completed_result() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.post(f"/documents/{DOCUMENT_ID}/ingest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": str(DOCUMENT_ID),
        "status": "completed",
        "chunks_created": 2,
    }


def test_document_ingest_hides_other_users_documents() -> None:
    setup_overrides(
        ingestion_service=FakeIngestionService(
            error=IngestionServiceError("Document not found.", status_code=404)
        )
    )
    client = TestClient(app)

    try:
        response = client.post(f"/documents/{DOCUMENT_ID}/ingest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_document_metadata_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post(f"/documents/{DOCUMENT_ID}/metadata")

    assert response.status_code == 401


def test_document_metadata_returns_extracted_metadata() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.post(f"/documents/{DOCUMENT_ID}/metadata")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": str(DOCUMENT_ID),
        "filename": "proposal.pdf",
        "summary": "A short proposal for Acme.",
        "metadata": {
            "document_type": "proposal",
            "title": "Acme Proposal",
            "summary": "A short proposal for Acme.",
            "entities": ["Acme"],
            "key_points": ["Implementation is planned."],
            "missing_information": [],
            "recommended_actions": ["Review scope."],
            "recommended_workflow": "proposal_review",
            "confidence": 0.84,
        },
    }


def test_document_metadata_hides_other_users_documents() -> None:
    setup_overrides(
        metadata_service=FakeMetadataService(
            error=DocumentMetadataServiceError("Document not found.", status_code=404)
        )
    )
    client = TestClient(app)

    try:
        response = client.post(f"/documents/{DOCUMENT_ID}/metadata")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_document_summary_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post(f"/documents/{DOCUMENT_ID}/summary")

    assert response.status_code == 401


def test_document_summary_returns_generated_summary() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.post(f"/documents/{DOCUMENT_ID}/summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": str(DOCUMENT_ID),
        "filename": "proposal.pdf",
        "summary": "Short summary.",
        "metadata": {
            "existing_field": "kept",
            "key_points": ["A key point"],
            "recommended_actions": ["Review next step"],
            "suggested_workflow": "proposal_review",
            "detailed_summary": "Detailed summary.",
        },
        "generated": {
            "concise_summary": "Short summary.",
            "detailed_summary": "Detailed summary.",
            "key_points": ["A key point"],
            "recommended_actions": ["Review next step"],
            "suggested_workflow": "proposal_review",
        },
    }


def test_document_summary_hides_other_users_documents() -> None:
    setup_overrides(
        summary_service=FakeSummaryService(
            error=DocumentSummaryServiceError("Document not found.", status_code=404)
        )
    )
    client = TestClient(app)

    try:
        response = client.post(f"/documents/{DOCUMENT_ID}/summary")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_document_proposal_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post(f"/documents/{DOCUMENT_ID}/proposal")

    assert response.status_code == 401


def test_document_proposal_returns_generated_proposal() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.post(f"/documents/{DOCUMENT_ID}/proposal")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": str(DOCUMENT_ID),
        "filename": "proposal.pdf",
        "proposal": {
            "proposal_title": "Acme Implementation Proposal",
            "executive_summary": "A proposal for Acme.",
            "client_problem": "Acme needs implementation support.",
            "proposed_solution": "Deliver BizFlow AI implementation support.",
            "scope_of_work": ["Discovery", "Implementation"],
            "deliverables": ["Configured workspace"],
            "timeline": [],
            "assumptions": ["Acme provides stakeholders."],
            "missing_information": ["Budget"],
            "next_steps": ["Confirm scope"],
        },
        "metadata": {
            "proposal_draft": {
                "proposal_title": "Acme Implementation Proposal",
                "executive_summary": "A proposal for Acme.",
                "client_problem": "Acme needs implementation support.",
                "proposed_solution": "Deliver BizFlow AI implementation support.",
                "scope_of_work": ["Discovery", "Implementation"],
                "deliverables": ["Configured workspace"],
                "timeline": [],
                "assumptions": ["Acme provides stakeholders."],
                "missing_information": ["Budget"],
                "next_steps": ["Confirm scope"],
            }
        },
    }


def test_document_proposal_hides_other_users_documents() -> None:
    setup_overrides(
        proposal_service=FakeProposalService(
            error=DocumentProposalServiceError("Document not found.", status_code=404)
        )
    )
    client = TestClient(app)

    try:
        response = client.post(f"/documents/{DOCUMENT_ID}/proposal")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_document_email_draft_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post(f"/documents/{DOCUMENT_ID}/email-draft")

    assert response.status_code == 401


def test_document_email_draft_returns_generated_draft() -> None:
    setup_overrides()
    client = TestClient(app)

    try:
        response = client.post(f"/documents/{DOCUMENT_ID}/email-draft")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": str(DOCUMENT_ID),
        "filename": "proposal.pdf",
        "email_draft": {
            "subject": "Proposal Follow-Up for Acme",
            "body": "Hi Acme team,\n\nThank you for sharing your brief.",
            "purpose": "proposal_follow_up",
            "recipient_context": "Client stakeholder",
            "missing_information_questions": ["What timeline should we plan around?"],
            "call_to_action": "Please confirm the preferred implementation timeline.",
        },
        "metadata": {
            "email_draft": {
                "subject": "Proposal Follow-Up for Acme",
                "body": "Hi Acme team,\n\nThank you for sharing your brief.",
                "purpose": "proposal_follow_up",
                "recipient_context": "Client stakeholder",
                "missing_information_questions": ["What timeline should we plan around?"],
                "call_to_action": "Please confirm the preferred implementation timeline.",
            }
        },
    }


def test_document_email_draft_hides_other_users_documents() -> None:
    setup_overrides(
        email_draft_service=FakeEmailDraftService(
            error=DocumentEmailDraftServiceError("Document not found.", status_code=404)
        )
    )
    client = TestClient(app)

    try:
        response = client.post(f"/documents/{DOCUMENT_ID}/email-draft")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
