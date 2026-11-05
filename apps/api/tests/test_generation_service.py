import pytest

from app.core.config import Settings
from app.services.generation_service import GenerationService, GenerationServiceError


class FakeGenerationResult:
    text = " Generated answer. "


class FakeModels:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def generate_content(self, *, model: str, contents: str) -> FakeGenerationResult:
        self.calls.append({"model": model, "contents": contents})
        return FakeGenerationResult()


class FakeClient:
    def __init__(self) -> None:
        self.models = FakeModels()


class FailingModels:
    def generate_content(self, *, model: str, contents: str) -> FakeGenerationResult:
        _ = model, contents
        raise RuntimeError("quota exceeded")


class QuotaError(Exception):
    status_code = 429


class QuotaModels:
    def generate_content(self, *, model: str, contents: str) -> FakeGenerationResult:
        _ = model, contents
        raise QuotaError("quota exceeded")


class FailingClient:
    def __init__(self) -> None:
        self.models = FailingModels()


class QuotaClient:
    def __init__(self) -> None:
        self.models = QuotaModels()


def test_generation_service_returns_generated_text() -> None:
    client = FakeClient()
    service = GenerationService(
        settings=Settings(
            gemini_api_key="test-key",
            default_chat_model="test-chat-model",
        ),
        client=client,
    )

    result = service.generate_text("Grounded prompt")

    assert result == "Generated answer."
    assert client.models.calls == [
        {
            "model": "test-chat-model",
            "contents": "Grounded prompt",
        }
    ]


def test_generation_service_wraps_provider_errors() -> None:
    service = GenerationService(
        settings=Settings(
            gemini_api_key="test-key",
            default_chat_model="test-chat-model",
        ),
        client=FailingClient(),
    )

    with pytest.raises(GenerationServiceError, match="Gemini answer generation failed."):
        service.generate_text("Grounded prompt")


def test_generation_service_preserves_provider_status_code() -> None:
    service = GenerationService(
        settings=Settings(
            gemini_api_key="test-key",
            default_chat_model="test-chat-model",
        ),
        client=QuotaClient(),
    )

    with pytest.raises(GenerationServiceError) as exc_info:
        service.generate_text("Grounded prompt")

    assert exc_info.value.status_code == 429
    assert str(exc_info.value) == (
        "Gemini quota was exceeded. Please retry later or configure a chat model with available "
        "quota."
    )
