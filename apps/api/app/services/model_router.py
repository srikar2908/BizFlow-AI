from dataclasses import dataclass
from typing import Any, Literal

ModelTask = Literal["chat", "embedding", "metadata_extraction", "proposal_generation"]


@dataclass(frozen=True)
class ModelRequest:
    task: ModelTask
    prompt: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ModelResponse:
    content: str
    provider: str
    model: str
    metadata: dict[str, Any]


class ModelRouter:
    """Single boundary for all model provider calls."""

    async def complete(self, request: ModelRequest) -> ModelResponse:
        # TODO: Route model calls through LiteLLM with Langfuse instrumentation.
        raise NotImplementedError("Model routing is not implemented yet.")
