from uuid import UUID

import pytest

from app.core.config import Settings
from app.services.document_metadata_service import MetadataChunk
from app.services.document_proposal_service import (
    DocumentProposalService,
    DocumentProposalServiceError,
    ProposalDocument,
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


class FakeProposalService(DocumentProposalService):
    def __init__(
        self,
        *,
        chunks: list[MetadataChunk],
        generation_response: str,
        document: ProposalDocument | None = None,
    ) -> None:
        self.fake_generation_service = FakeGenerationService(generation_response)
        super().__init__(
            settings=Settings(
                supabase_url="https://example.supabase.co",
                supabase_anon_key="anon",
            ),
            generation_service=self.fake_generation_service,  # type: ignore[arg-type]
        )
        self.document = document or ProposalDocument(
            id=DOCUMENT_ID,
            filename="proposal.pdf",
            status="completed",
            summary="Existing summary.",
            metadata={"document_type": "proposal", "entities": ["Acme"]},
        )
        self.chunks = chunks
        self.saved_metadata: dict[str, object] | None = None

    async def _get_document(
        self,
        *,
        document_id: UUID,
        user_id: UUID,
        access_token: str,
    ) -> ProposalDocument:
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
        metadata: dict[str, object],
    ) -> None:
        assert document_id == DOCUMENT_ID
        assert user_id == USER_ID
        assert access_token == "test-access-token"
        self.saved_metadata = metadata


def proposal_json() -> str:
    return """
    {
      "proposal_title": "Acme Implementation Proposal",
      "executive_summary": "A proposal for Acme.",
      "client_problem": "Acme needs implementation support.",
      "proposed_solution": "Deliver BizFlow AI implementation support.",
      "scope_of_work": ["Discovery", "Implementation"],
      "deliverables": ["Configured workspace"],
      "timeline": [],
      "assumptions": ["Acme provides stakeholders."],
      "missing_information": ["Budget"],
      "next_steps": ["Confirm scope"]
    }
    """


@pytest.mark.asyncio
async def test_proposal_generation_returns_and_saves_valid_json() -> None:
    service = FakeProposalService(
        chunks=[MetadataChunk(chunk_index=0, content="Acme proposal content.", metadata={})],
        generation_response=proposal_json(),
    )

    result = await service.generate_proposal(
        document_id=DOCUMENT_ID,
        user_id=USER_ID,
        access_token="test-access-token",
    )

    assert result.proposal.proposal_title == "Acme Implementation Proposal"
    assert service.saved_metadata == {
        "document_type": "proposal",
        "entities": ["Acme"],
        "proposal_draft": result.proposal.model_dump(mode="json"),
    }
    assert "Existing summary." in service.fake_generation_service.prompts[0]
    assert "Acme proposal content." in service.fake_generation_service.prompts[0]


@pytest.mark.asyncio
async def test_proposal_generation_requires_chunks() -> None:
    service = FakeProposalService(chunks=[], generation_response=proposal_json())

    with pytest.raises(DocumentProposalServiceError) as exc_info:
        await service.generate_proposal(
            document_id=DOCUMENT_ID,
            user_id=USER_ID,
            access_token="test-access-token",
        )

    assert exc_info.value.status_code == 400
    assert str(exc_info.value) == "Document must be ingested before a proposal can be generated."
    assert service.fake_generation_service.prompts == []


@pytest.mark.asyncio
async def test_proposal_generation_rejects_invalid_json() -> None:
    service = FakeProposalService(
        chunks=[MetadataChunk(chunk_index=0, content="Acme proposal", metadata={})],
        generation_response="not json",
    )

    with pytest.raises(DocumentProposalServiceError) as exc_info:
        await service.generate_proposal(
            document_id=DOCUMENT_ID,
            user_id=USER_ID,
            access_token="test-access-token",
        )

    assert exc_info.value.status_code == 502
    assert str(exc_info.value) == "Proposal generation returned invalid JSON."
    assert service.saved_metadata is None
