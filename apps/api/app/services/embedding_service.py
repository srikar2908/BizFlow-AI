from collections.abc import Sequence
from typing import Any, Protocol, cast

from google import genai

from app.core.config import Settings, get_settings


class EmbeddingClient(Protocol):
    models: Any


class EmbeddingService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: EmbeddingClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or genai.Client(api_key=self.settings.gemini_api_key)

    def embed_text(self, text: str) -> list[float]:
        result = self.client.models.embed_content(
            model=self.settings.default_embedding_model,
            contents=text,
        )
        embeddings = cast(Sequence[Any], result.embeddings)
        first_embedding = embeddings[0]
        values = cast(Sequence[float], first_embedding.values)

        return list(values)
