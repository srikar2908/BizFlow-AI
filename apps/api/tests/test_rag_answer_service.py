from uuid import UUID

import pytest

from app.core.security import CurrentUser
from app.schemas.rag import RagSearchResult
from app.services.observability_service import ObservabilityService
from app.services.rag_answer_service import NOT_ENOUGH_CONTEXT_MESSAGE, RagAnswerService

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000201")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000101")


class FakeSearchService:
    def __init__(self, results: list[RagSearchResult]) -> None:
        self.results = results
        self.calls: list[dict[str, object]] = []

    async def search(
        self,
        *,
        query: str,
        match_count: int,
        user_id: UUID,
        access_token: str,
    ) -> list[RagSearchResult]:
        self.calls.append(
            {
                "query": query,
                "match_count": match_count,
                "user_id": user_id,
                "access_token": access_token,
            }
        )
        return self.results


class FakeGenerationService:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "The document says this is a BizFlow AI test document."


class FailingLangfuseClient:
    def start_observation(self, **kwargs: object) -> object:
        raise RuntimeError("langfuse unavailable")


def user() -> CurrentUser:
    return CurrentUser(id=USER_ID, email="owner@example.com", access_token="token")


@pytest.mark.asyncio
async def test_rag_answer_service_generates_grounded_answer_with_citations() -> None:
    search_service = FakeSearchService(
        [
            RagSearchResult(
                chunk_id=CHUNK_ID,
                document_id=DOCUMENT_ID,
                filename="bizflow-test.txt",
                chunk_index=0,
                content="This is a BizFlow AI test document.",
                similarity=0.91,
            )
        ]
    )
    generation_service = FakeGenerationService()
    service = RagAnswerService(
        search_service=search_service,  # type: ignore[arg-type]
        generation_service=generation_service,  # type: ignore[arg-type]
    )

    response = await service.answer(query="What is this?", match_count=5, current_user=user())

    assert response.answer == "The document says this is a BizFlow AI test document."
    assert response.citations[0].filename == "bizflow-test.txt"
    assert response.citations[0].chunk_index == 0
    assert response.citations[0].preview == "This is a BizFlow AI test document."
    assert search_service.calls == [
        {
            "query": "What is this?",
            "match_count": 5,
            "user_id": USER_ID,
            "access_token": "token",
        }
    ]
    assert "What is this?" in generation_service.prompts[0]
    assert "bizflow-test.txt" in generation_service.prompts[0]
    assert "Chunk index: 0" in generation_service.prompts[0]


@pytest.mark.asyncio
async def test_rag_answer_service_skips_llm_when_no_chunks_found() -> None:
    search_service = FakeSearchService([])
    generation_service = FakeGenerationService()
    service = RagAnswerService(
        search_service=search_service,  # type: ignore[arg-type]
        generation_service=generation_service,  # type: ignore[arg-type]
    )

    response = await service.answer(query="Unknown?", match_count=5, current_user=user())

    assert response.answer == NOT_ENOUGH_CONTEXT_MESSAGE
    assert response.citations == []
    assert generation_service.prompts == []


@pytest.mark.asyncio
async def test_rag_answer_service_succeeds_when_observability_fails() -> None:
    search_service = FakeSearchService(
        [
            RagSearchResult(
                chunk_id=CHUNK_ID,
                document_id=DOCUMENT_ID,
                filename="bizflow-test.txt",
                chunk_index=0,
                content="This is a BizFlow AI test document.",
                similarity=0.91,
            )
        ]
    )
    generation_service = FakeGenerationService()
    observability_service = ObservabilityService(
        client=FailingLangfuseClient(),
    )
    observability_service.enabled = True
    service = RagAnswerService(
        search_service=search_service,  # type: ignore[arg-type]
        generation_service=generation_service,  # type: ignore[arg-type]
        observability_service=observability_service,
    )

    response = await service.answer(query="What is this?", match_count=5, current_user=user())

    assert response.answer == "The document says this is a BizFlow AI test document."
    assert response.citations[0].filename == "bizflow-test.txt"
