from app.core.config import Settings
from app.services.embedding_service import EmbeddingService


class FakeEmbedding:
    values = [0.1, 0.2, 0.3]


class FakeEmbeddingResult:
    embeddings = [FakeEmbedding()]


class FakeModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def embed_content(self, *, model: str, contents: str) -> FakeEmbeddingResult:
        self.calls.append({"model": model, "contents": contents})
        return FakeEmbeddingResult()


class FakeClient:
    def __init__(self) -> None:
        self.models = FakeModels()


def test_embedding_service_returns_embedding_values() -> None:
    client = FakeClient()
    service = EmbeddingService(
        settings=Settings(
            gemini_api_key="test-key",
            default_embedding_model="test-embedding-model",
        ),
        client=client,
    )

    result = service.embed_text("BizFlow AI")

    assert result == [0.1, 0.2, 0.3]
    assert client.models.calls == [
        {
            "model": "test-embedding-model",
            "contents": "BizFlow AI",
        }
    ]
