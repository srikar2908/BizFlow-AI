from uuid import UUID

import pytest

from app.core.config import Settings
from app.schemas.documents import DocumentMetadata
from app.services.document_metadata_service import (
    DocumentMetadataService,
    DocumentMetadataServiceError,
    MetadataChunk,
    MetadataDocument,
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


class FakeMetadataService(DocumentMetadataService):
    def __init__(self, *, chunks: list[MetadataChunk], generation_response: str) -> None:
        self.fake_generation_service = FakeGenerationService(generation_response)
        super().__init__(
            settings=Settings(
                supabase_url="https://example.supabase.co",
                supabase_anon_key="anon",
            ),
            generation_service=self.fake_generation_service,  # type: ignore[arg-type]
        )
        self.chunks = chunks
        self.saved_metadata: DocumentMetadata | None = None

    async def _get_document(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> MetadataDocument:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        return MetadataDocument(id=document_id, filename="proposal.pdf")

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
        metadata: DocumentMetadata,
    ) -> None:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        self.saved_metadata = metadata


def metadata_json() -> str:
    return """
    {
      "document_type": "proposal",
      "title": "Acme Proposal",
      "summary": "A proposal for Acme.",
      "entities": ["Acme"],
      "key_points": ["Implementation timeline is included."],
      "missing_information": [],
      "recommended_actions": ["Review commercial terms."],
      "recommended_workflow": "proposal_review",
      "confidence": 0.86
    }
    """


@pytest.mark.asyncio
async def test_metadata_extraction_saves_valid_json() -> None:
    service = FakeMetadataService(
        chunks=[
            MetadataChunk(
                chunk_index=0,
                content="Acme needs an implementation proposal.",
                metadata={"page_number": 1},
            )
        ],
        generation_response=metadata_json(),
    )

    result = await service.extract_metadata(
        document_id=DOCUMENT_ID,
        user_id=USER_ID,
        access_token="test-access-token",
    )

    assert result.metadata.document_type == "proposal"
    assert result.summary == "A proposal for Acme."
    assert service.saved_metadata == result.metadata
    assert "Acme needs an implementation proposal." in service.fake_generation_service.prompts[0]
    assert "Page: 1" in service.fake_generation_service.prompts[0]


@pytest.mark.asyncio
async def test_metadata_extraction_requires_ingested_chunks() -> None:
    service = FakeMetadataService(chunks=[], generation_response=metadata_json())

    with pytest.raises(DocumentMetadataServiceError) as exc_info:
        await service.extract_metadata(
            document_id=DOCUMENT_ID,
            user_id=USER_ID,
            access_token="test-access-token",
        )

    assert exc_info.value.status_code == 400
    assert str(exc_info.value) == "Document must be ingested before metadata can be extracted."
    assert service.fake_generation_service.prompts == []


@pytest.mark.asyncio
async def test_metadata_extraction_rejects_invalid_json() -> None:
    service = FakeMetadataService(
        chunks=[MetadataChunk(chunk_index=0, content="Acme proposal", metadata={})],
        generation_response="not json",
    )

    with pytest.raises(DocumentMetadataServiceError) as exc_info:
        await service.extract_metadata(
            document_id=DOCUMENT_ID,
            user_id=USER_ID,
            access_token="test-access-token",
        )

    assert exc_info.value.status_code == 502
    assert str(exc_info.value) == "Metadata extraction returned invalid JSON."
    assert service.saved_metadata is None
