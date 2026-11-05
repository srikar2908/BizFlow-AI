from typing import Any
from uuid import UUID

import pytest

from app.core.config import Settings
from app.services.document_email_draft_service import (
    DocumentEmailDraftService,
    DocumentEmailDraftServiceError,
    EmailDraftDocument,
)
from app.services.document_metadata_service import MetadataChunk

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000101")


class FakeGenerationService:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class FakeEmailDraftService(DocumentEmailDraftService):
    def __init__(
        self,
        *,
        chunks: list[MetadataChunk],
        generation_response: str,
        document: EmailDraftDocument | None = None,
    ) -> None:
        self.fake_generation_service = FakeGenerationService(generation_response)
        super().__init__(
            settings=Settings(
                supabase_url="https://example.supabase.co",
                supabase_anon_key="anon",
            ),
            generation_service=self.fake_generation_service,  # type: ignore[arg-type]
        )
        self.document = document or EmailDraftDocument(
            id=DOCUMENT_ID,
            filename="proposal.pdf",
            status="completed",
            summary="Existing summary.",
            metadata={
                "document_type": "proposal",
                "proposal_draft": {"proposal_title": "Acme Implementation Proposal"},
            },
        )
        self.chunks = chunks
        self.saved_metadata: dict[str, Any] | None = None

    async def _get_document(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> EmailDraftDocument:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        return self.document

    async def _get_document_chunks(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> list[MetadataChunk]:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        return self.chunks

    async def _update_document_metadata(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
        metadata: dict[str, Any],
    ) -> None:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        self.saved_metadata = metadata


def email_draft_json() -> str:
    return """
    {
      "subject": "Proposal Follow-Up for Acme",
      "body": "Hi Acme team,\\n\\nThank you for sharing your brief.",
      "purpose": "proposal_follow_up",
      "recipient_context": "Client stakeholder",
      "missing_information_questions": ["What timeline should we plan around?"],
      "call_to_action": "Please confirm the preferred implementation timeline."
    }
    """


@pytest.mark.asyncio
async def test_email_draft_generation_returns_and_saves_valid_json() -> None:
    service = FakeEmailDraftService(
        chunks=[MetadataChunk(chunk_index=0, content="Acme proposal content.", metadata={})],
        generation_response=email_draft_json(),
    )

    result = await service.generate_email_draft(
        document_id=DOCUMENT_ID,
        user_id=USER_ID,
        access_token="test-access-token",
    )

    assert result.email_draft.subject == "Proposal Follow-Up for Acme"
    assert service.saved_metadata == {
        "document_type": "proposal",
        "proposal_draft": {"proposal_title": "Acme Implementation Proposal"},
        "email_draft": result.email_draft.model_dump(mode="json"),
    }
    assert "Existing summary." in service.fake_generation_service.prompts[0]
    assert "Acme proposal content." in service.fake_generation_service.prompts[0]
    assert "Acme Implementation Proposal" in service.fake_generation_service.prompts[0]


@pytest.mark.asyncio
async def test_email_draft_generation_requires_chunks() -> None:
    service = FakeEmailDraftService(chunks=[], generation_response=email_draft_json())

    with pytest.raises(DocumentEmailDraftServiceError) as exc_info:
        await service.generate_email_draft(
            document_id=DOCUMENT_ID,
            user_id=USER_ID,
            access_token="test-access-token",
        )

    assert exc_info.value.status_code == 400
    assert (
        str(exc_info.value) == "Document must be ingested before an email draft can be generated."
    )
    assert service.fake_generation_service.prompts == []


@pytest.mark.asyncio
async def test_email_draft_generation_rejects_invalid_json() -> None:
    service = FakeEmailDraftService(
        chunks=[MetadataChunk(chunk_index=0, content="Acme proposal", metadata={})],
        generation_response="not json",
    )

    with pytest.raises(DocumentEmailDraftServiceError) as exc_info:
        await service.generate_email_draft(
            document_id=DOCUMENT_ID,
            user_id=USER_ID,
            access_token="test-access-token",
        )

    assert exc_info.value.status_code == 502
    assert str(exc_info.value) == "Email draft generation returned invalid JSON."
    assert service.saved_metadata is None
