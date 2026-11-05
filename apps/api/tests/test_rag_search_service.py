from uuid import UUID

import httpx
import pytest

from app.core.config import Settings
from app.services.rag_search_service import RagSearchService

USER_ID = UUID("00000000-0000-0000-0000-000000000001")


class FakeEmbeddingService:
    def __init__(self) -> None:
        self.inputs: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        self.inputs.append(text)
        return [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_rag_search_service_uses_mocked_query_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_post(
        self: httpx.AsyncClient,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        _ = self
        captured["url"] = url
        captured["kwargs"] = kwargs
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json=[
                {
                    "chunk_id": "00000000-0000-0000-0000-000000000201",
                    "document_id": "00000000-0000-0000-0000-000000000101",
                    "filename": "bizflow-test.txt",
                    "chunk_index": 0,
                    "content": "This is a BizFlow AI test document.",
                    "similarity": 0.91,
                }
            ],
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    embedding_service = FakeEmbeddingService()
    service = RagSearchService(
        settings=Settings(
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
        ),
        embedding_service=embedding_service,  # type: ignore[arg-type]
    )

    results = await service.search(
        query="test document",
        match_count=3,
        user_id=USER_ID,
        access_token="access-token",
    )

    assert embedding_service.inputs == ["test document"]
    assert results[0].filename == "bizflow-test.txt"
    assert captured["url"] == "https://example.supabase.co/rest/v1/rpc/match_document_chunks"
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["json"] == {
        "query_embedding": [0.1, 0.2, 0.3],
        "match_count": 3,
        "match_user_id": str(USER_ID),
    }


@pytest.mark.asyncio
async def test_rag_search_service_accepts_live_rpc_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_post(
        self: httpx.AsyncClient,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        _ = self, kwargs
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json=[
                {
                    "id": "00000000-0000-0000-0000-000000000201",
                    "document_id": "00000000-0000-0000-0000-000000000101",
                    "filename": "bizflow-test.txt",
                    "chunk_index": 0,
                    "content": "This is a BizFlow AI test document.",
                    "score": 0.91,
                }
            ],
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    service = RagSearchService(
        settings=Settings(
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
        ),
        embedding_service=FakeEmbeddingService(),  # type: ignore[arg-type]
    )

    results = await service.search(
        query="test document",
        match_count=3,
        user_id=USER_ID,
        access_token="access-token",
    )

    assert str(results[0].chunk_id) == "00000000-0000-0000-0000-000000000201"
    assert results[0].similarity == 0.91
