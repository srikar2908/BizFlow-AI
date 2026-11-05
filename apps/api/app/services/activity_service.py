import logging
from uuid import UUID

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class ActivityService:
    """Best-effort append-only activity logging using the backend service credential."""

    def __init__(self, settings: Settings) -> None:
        self.url = settings.supabase_url.rstrip("/")
        self.key = settings.supabase_service_role_key

    async def record(
        self, *, user_id: UUID, document_id: UUID | None, event_type: str, filename: str | None
    ) -> None:
        if not self.url or not self.key:
            return
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.url}/rest/v1/activity_events",
                    headers={
                        "apikey": self.key,
                        "Authorization": f"Bearer {self.key}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal",
                    },
                    json={
                        "user_id": str(user_id),
                        "document_id": str(document_id) if document_id else None,
                        "event_type": event_type,
                        "details": {"filename": filename} if filename else {},
                    },
                )
            if response.status_code >= 400:
                logger.warning(
                    "Activity event write failed: event_type=%s status=%s",
                    event_type,
                    response.status_code,
                )
        except Exception as exc:
            # Activity history is auxiliary: never turn an already successful
            # document/workflow operation into a failure because logging failed.
            logger.warning(
                "Activity event write failed: event_type=%s error_type=%s",
                event_type,
                type(exc).__name__,
            )
