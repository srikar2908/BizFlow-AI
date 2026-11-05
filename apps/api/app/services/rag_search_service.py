import logging
from typing import Any, cast
from uuid import UUID

import httpx

from app.core.config import Settings, get_settings
from app.schemas.rag import RagSearchResult
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RagSearchServiceError(Exception):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class RagSearchService:
    def __init__(
        self,
        settings: Settings | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedding_service = embedding_service or EmbeddingService(self.settings)
        self.supabase_url = self.settings.supabase_url.rstrip("/")
        self.supabase_anon_key = self.settings.supabase_anon_key

    async def search(
        self,
        *,
        query: str,
        match_count: int,
        user_id: UUID,
        access_token: str,
    ) -> list[RagSearchResult]:
        embedding = self.embedding_service.embed_text(query)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.supabase_url}/rest/v1/rpc/match_document_chunks",
                headers={
                    **self._database_headers(access_token),
                    "Content-Type": "application/json",
                },
                json={
                    "query_embedding": embedding,
                    "match_count": match_count,
                    "match_user_id": str(user_id),
                },
            )

        self._raise_for_supabase_error(response)
        payload = response.json()
        if not isinstance(payload, list):
            raise RagSearchServiceError("Unexpected RAG search response from Supabase.")

        return [self._result_from_row(row) for row in cast(list[dict[str, Any]], payload)]

    def _database_headers(self, access_token: str) -> dict[str, str]:
        if not self.supabase_anon_key or not access_token:
            raise RagSearchServiceError("Supabase RAG search access is not configured.")

        return {
            "apikey": self.supabase_anon_key,
            "Authorization": f"Bearer {access_token}",
        }

    @staticmethod
    def _result_from_row(row: dict[str, Any]) -> RagSearchResult:
        try:
            chunk_id = row.get("chunk_id") or row.get("id")
            similarity = row.get("similarity")
            if similarity is None:
                similarity = row.get("score")
            if chunk_id is None or similarity is None:
                raise KeyError("chunk_id/similarity")

            return RagSearchResult(
                chunk_id=chunk_id,
                document_id=row["document_id"],
                filename=row["filename"],
                chunk_index=row["chunk_index"],
                content=row["content"],
                similarity=similarity,
            )
        except KeyError as exc:
            logger.warning("Unexpected RAG search row keys: keys=%s", sorted(row.keys()))
            raise RagSearchServiceError("Unexpected RAG search response from Supabase.") from exc

    @staticmethod
    def _raise_for_supabase_error(response: httpx.Response) -> None:
        if response.status_code >= 400:
            logger.warning(
                "Supabase RAG search error: status_code=%s path=%s body=%s",
                response.status_code,
                response.request.url.path,
                response.text,
            )
            raise RagSearchServiceError("Unable to search document chunks.")
