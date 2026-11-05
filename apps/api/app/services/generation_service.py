import logging
from typing import Any, Protocol

from google import genai

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class GenerationClient(Protocol):
    models: Any


class GenerationServiceError(Exception):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class GenerationService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: GenerationClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or genai.Client(api_key=self.settings.gemini_api_key)

    def generate_text(self, prompt: str) -> str:
        if self.settings.default_chat_provider != "gemini":
            raise GenerationServiceError("Configured chat provider is not supported.")

        logger.info(
            "Generating text with Gemini: model=%s gemini_api_key_configured=%s",
            self.settings.default_chat_model,
            bool(self.settings.gemini_api_key),
        )
        try:
            result = self.client.models.generate_content(
                model=self.settings.default_chat_model,
                contents=prompt,
            )
        except Exception as exc:
            logger.warning(
                "Gemini answer generation failed: model=%s exception_type=%s message=%s",
                self.settings.default_chat_model,
                type(exc).__name__,
                str(exc),
            )
            raise GenerationServiceError(
                _provider_error_message(exc),
                status_code=_provider_status_code(exc),
            ) from exc

        text = getattr(result, "text", None)
        candidates = getattr(result, "candidates", None)
        logger.info(
            "Gemini answer response shape: model=%s response_type=%s has_text=%s "
            "candidates_count=%s",
            self.settings.default_chat_model,
            type(result).__name__,
            isinstance(text, str),
            len(candidates) if isinstance(candidates, list) else None,
        )
        if isinstance(text, str) and text.strip():
            return text.strip()

        raise GenerationServiceError("Gemini returned an empty answer.")


def _provider_status_code(exc: Exception) -> int:
    status_code = getattr(exc, "status_code", None)
    return status_code if isinstance(status_code, int) else 502


def _provider_error_message(exc: Exception) -> str:
    status_code = _provider_status_code(exc)
    if status_code == 429:
        return (
            "Gemini quota was exceeded. Please retry later or configure a chat model with "
            "available quota."
        )
    return "Gemini answer generation failed."
