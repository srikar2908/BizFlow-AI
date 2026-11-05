from uuid import UUID

import pytest

from app.core.config import Settings
from app.schemas.documents import DocumentSummaryGeneration
from app.services.document_metadata_service import MetadataChunk
from app.services.document_summary_service import (
    DocumentSummaryService,
    DocumentSummaryServiceError,
    SummaryDocument,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000101")


class FakeGenerationService:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class FakeSummaryService(DocumentSummaryService):
    def __init__(
        self,
        *,
        chunks: list[MetadataChunk],
        generation_response: str,
        document: SummaryDocument | None = None,
    ) -> None:
        self.fake_generation_service = FakeGenerationService(generation_response)
        super().__init__(
            settings=Settings(
                supabase_url="https://example.supabase.co",
                supabase_anon_key="anon",
            ),
            generation_service=self.fake_generation_service,  # type: ignore[arg-type]
        )
        self.document = document or SummaryDocument(
            id=DOCUMENT_ID,
            filename="proposal.pdf",
            status="completed",
            metadata={"document_type": "proposal", "entities": ["Acme"]},
        )
        self.chunks = chunks
        self.saved_summary: DocumentSummaryGeneration | None = None
        self.saved_metadata: dict[str, object] | None = None

    async def _get_document(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> SummaryDocument:
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

    async def _update_document_summary(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
        summary: DocumentSummaryGeneration,
        metadata: dict[str, object],
    ) -> None:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        self.saved_summary = summary
        self.saved_metadata = metadata


def summary_json() -> str:
    return """
    {
      "concise_summary": "A concise Acme proposal summary.",
      "detailed_summary": "A detailed Acme proposal summary.",
      "key_points": ["Timeline is included."],
      "recommended_actions": ["Review pricing."],
      "suggested_workflow": "proposal_review"
    }
    """


@pytest.mark.asyncio
async def test_summary_generation_saves_summary_and_merges_metadata() -> None:
    service = FakeSummaryService(
        chunks=[MetadataChunk(chunk_index=0, content="Acme proposal content.", metadata={})],
        generation_response=summary_json(),
    )

    result = await service.generate_summary(
        document_id=DOCUMENT_ID,
        user_id=USER_ID,
        access_token="test-access-token",
    )

    assert result.summary == "A concise Acme proposal summary."
    assert service.saved_summary == result.generated
    assert service.saved_metadata == {
        "document_type": "proposal",
        "entities": ["Acme"],
        "key_points": ["Timeline is included."],
        "recommended_actions": ["Review pricing."],
        "suggested_workflow": "proposal_review",
        "detailed_summary": "A detailed Acme proposal summary.",
    }


@pytest.mark.asyncio
async def test_summary_generation_requires_completed_document() -> None:
    service = FakeSummaryService(
        chunks=[MetadataChunk(chunk_index=0, content="Draft content.", metadata={})],
        generation_response=summary_json(),
        document=SummaryDocument(
            id=DOCUMENT_ID,
            filename="proposal.pdf",
            status="pending",
            metadata={},
        ),
    )

    with pytest.raises(DocumentSummaryServiceError) as exc_info:
        await service.generate_summary(
            document_id=DOCUMENT_ID,
            user_id=USER_ID,
            access_token="test-access-token",
        )

    assert exc_info.value.status_code == 400
    assert str(exc_info.value) == "Document must be completed before a summary can be generated."
    assert service.fake_generation_service.prompts == []


@pytest.mark.asyncio
async def test_summary_generation_requires_chunks() -> None:
    service = FakeSummaryService(chunks=[], generation_response=summary_json())

    with pytest.raises(DocumentSummaryServiceError) as exc_info:
        await service.generate_summary(
            document_id=DOCUMENT_ID,
            user_id=USER_ID,
            access_token="test-access-token",
        )

    assert exc_info.value.status_code == 400
    assert str(exc_info.value) == "Document must be ingested before a summary can be generated."
    assert service.fake_generation_service.prompts == []
