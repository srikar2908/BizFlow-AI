from uuid import UUID

import pytest

from app.core.config import Settings
from app.services.observability_service import ObservabilityService

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000101")


class FakeSpan:
    def __init__(self, *, fail_update: bool = False, fail_end: bool = False) -> None:
        self.fail_update = fail_update
        self.fail_end = fail_end
        self.updates: list[dict[str, object]] = []
        self.ended = False

    def update(self, **kwargs: object) -> None:
        if self.fail_update:
            raise RuntimeError("langfuse update failed")
        self.updates.append(kwargs)

    def end(self) -> None:
        if self.fail_end:
            raise RuntimeError("langfuse end failed")
        self.ended = True


class FakeLangfuseClient:
    def __init__(
        self,
        *,
        fail_start: bool = False,
        fail_update: bool = False,
        fail_end: bool = False,
    ) -> None:
        self.fail_start = fail_start
        self.span = FakeSpan(fail_update=fail_update, fail_end=fail_end)
        self.observations: list[dict[str, object]] = []

    def start_observation(self, **kwargs: object) -> FakeSpan:
        if self.fail_start:
            raise RuntimeError("langfuse start failed")
        self.observations.append(kwargs)
        return self.span


def test_observability_noops_when_disabled() -> None:
    service = ObservabilityService(
        Settings(langfuse_enabled=False, langfuse_public_key="", langfuse_secret_key="")
    )

    with service.trace(
        operation="metadata_extraction",
        user_id=USER_ID,
        document_id=DOCUMENT_ID,
        model="gemini-2.5-flash",
    ):
        pass

    assert service.enabled is False
    assert service.client is None


def test_observability_records_safe_success_metadata() -> None:
    client = FakeLangfuseClient()
    service = ObservabilityService(
        Settings(
            langfuse_enabled=True,
            langfuse_public_key="public",
            langfuse_secret_key="secret",
        ),
        client=client,
    )

    with service.trace(
        operation="document_summary",
        user_id=USER_ID,
        document_id=DOCUMENT_ID,
        model="gemini-2.5-flash",
        metadata={"chunks_count": 2},
    ):
        pass

    assert client.observations[0]["name"] == "document_summary"
    assert client.observations[0]["model"] == "gemini-2.5-flash"
    update_metadata = client.span.updates[0]["metadata"]
    assert isinstance(update_metadata, dict)
    assert update_metadata["success"] is True
    assert update_metadata["user_id"] == str(USER_ID)
    assert update_metadata["document_id"] == str(DOCUMENT_ID)
    assert update_metadata["chunks_count"] == 2
    assert "latency_ms" in update_metadata
    assert client.span.ended is True


def test_observability_records_failure_without_swallowing_error() -> None:
    client = FakeLangfuseClient()
    service = ObservabilityService(
        Settings(
            langfuse_enabled=True,
            langfuse_public_key="public",
            langfuse_secret_key="secret",
        ),
        client=client,
    )

    with (
        pytest.raises(ValueError, match="bad generation"),
        service.trace(operation="proposal_generation", user_id=USER_ID),
    ):
        raise ValueError("bad generation")

    update = client.span.updates[0]
    update_metadata = update["metadata"]
    assert isinstance(update_metadata, dict)
    assert update_metadata["success"] is False
    assert update_metadata["error_type"] == "ValueError"
    assert update["level"] == "ERROR"
    assert update["status_message"] == "bad generation"
    assert client.span.ended is True


def test_observability_start_failure_does_not_break_operation() -> None:
    client = FakeLangfuseClient(fail_start=True)
    service = ObservabilityService(
        Settings(
            langfuse_enabled=True,
            langfuse_public_key="public",
            langfuse_secret_key="secret",
        ),
        client=client,
    )
    operation_ran = False

    with service.trace(operation="rag_answer", user_id=USER_ID):
        operation_ran = True

    assert operation_ran is True
    assert client.observations == []


def test_observability_update_and_end_failures_do_not_break_operation() -> None:
    client = FakeLangfuseClient(fail_update=True, fail_end=True)
    service = ObservabilityService(
        Settings(
            langfuse_enabled=True,
            langfuse_public_key="public",
            langfuse_secret_key="secret",
        ),
        client=client,
    )
    operation_ran = False

    with service.trace(operation="rag_answer", user_id=USER_ID):
        operation_ran = True

    assert operation_ran is True
    assert client.observations[0]["name"] == "rag_answer"
