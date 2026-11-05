import hashlib
import logging
import re
from datetime import datetime
from typing import Any, cast
from uuid import UUID

import httpx

from app.core.config import Settings
from app.schemas.documents import DocumentStatus, DocumentSummary, DocumentUploadResponse

logger = logging.getLogger(__name__)


class DocumentServiceError(Exception):
    """Raised when a document persistence operation fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.code = self._extract_error_code(body)

    @staticmethod
    def _extract_error_code(body: str | None) -> str | None:
        if body is None:
            return None

        try:
            payload = httpx.Response(200, content=body).json()
        except ValueError:
            return None

        if not isinstance(payload, dict):
            return None

        code = payload.get("code")
        return code if isinstance(code, str) else None


class DocumentService:
    """Document workflow boundary."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.supabase_url = settings.supabase_url.rstrip("/")
        self.supabase_anon_key = settings.supabase_anon_key
        self.service_role_key = settings.supabase_service_role_key
        self.bucket = settings.supabase_storage_bucket

    async def list_documents_for_user(
        self,
        *,
        user_id: UUID,
        access_token: str,
    ) -> list[DocumentSummary]:
        try:
            rows = await self._select_documents(
                user_id=user_id,
                access_token=access_token,
                select="id,filename,status,created_at,summary,metadata",
            )
        except DocumentServiceError as exc:
            if exc.code == "PGRST205":
                return []
            raise
        return [self._summary_from_row(row) for row in rows]

    async def upload_document(
        self,
        *,
        user_id: UUID,
        access_token: str,
        filename: str,
        mime_type: str | None,
        content: bytes,
    ) -> DocumentUploadResponse:
        file_hash = hashlib.sha256(content).hexdigest()
        duplicate = await self._find_duplicate(
            user_id=user_id,
            access_token=access_token,
            file_hash=file_hash,
        )

        if duplicate is not None:
            summary = self._summary_from_row(duplicate)
            return DocumentUploadResponse(**summary.model_dump(), duplicate=True)

        storage_path = self._storage_path(
            user_id=user_id,
            file_hash=file_hash,
            filename=filename,
        )
        await self._upload_to_storage(
            storage_path=storage_path,
            content=content,
            mime_type=mime_type,
        )
        inserted = await self._insert_document(
            user_id=user_id,
            access_token=access_token,
            filename=filename,
            file_hash=file_hash,
            mime_type=mime_type,
            size_bytes=len(content),
            storage_path=storage_path,
        )
        summary = self._summary_from_row(inserted)
        return DocumentUploadResponse(**summary.model_dump(), duplicate=False)

    async def _select_documents(
        self,
        *,
        user_id: UUID,
        access_token: str,
        select: str,
        extra_params: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        self._require_supabase_config()
        params = {
            "select": select,
            "user_id": f"eq.{user_id}",
            "order": "created_at.desc",
        }
        if extra_params is not None:
            params.update(extra_params)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.supabase_url}/rest/v1/documents",
                headers=self._database_headers(access_token),
                params=params,
            )

        self._raise_for_supabase_error(response, "Unable to read documents.")
        payload = response.json()
        if not isinstance(payload, list):
            raise DocumentServiceError("Unexpected documents response from Supabase.")
        return cast(list[dict[str, Any]], payload)

    async def _find_duplicate(
        self,
        *,
        user_id: UUID,
        access_token: str,
        file_hash: str,
    ) -> dict[str, Any] | None:
        rows = await self._select_documents(
            user_id=user_id,
            access_token=access_token,
            select="id,filename,status,created_at,summary,metadata",
            extra_params={"file_hash": f"eq.{file_hash}", "limit": "1"},
        )
        return rows[0] if rows else None

    async def _upload_to_storage(
        self,
        *,
        storage_path: str,
        content: bytes,
        mime_type: str | None,
    ) -> None:
        self._require_supabase_config()
        headers = self._headers()
        headers["Content-Type"] = mime_type or "application/octet-stream"
        headers["x-upsert"] = "false"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.supabase_url}/storage/v1/object/{self.bucket}/{storage_path}",
                headers=headers,
                content=content,
            )

        self._raise_for_supabase_error(response, "Unable to store document upload.")

    async def _insert_document(
        self,
        *,
        user_id: UUID,
        access_token: str,
        filename: str,
        file_hash: str,
        mime_type: str | None,
        size_bytes: int,
        storage_path: str,
    ) -> dict[str, Any]:
        self._require_supabase_config()
        payload = {
            "user_id": str(user_id),
            "filename": filename,
            "file_hash": file_hash,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "storage_path": storage_path,
            "status": "pending",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.supabase_url}/rest/v1/documents",
                headers={
                    **self._database_headers(access_token),
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                json=payload,
                params={"select": "id,filename,status,created_at,summary,metadata"},
            )

        self._raise_for_supabase_error(response, "Unable to create document row.")
        data = response.json()
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            raise DocumentServiceError("Unexpected document insert response from Supabase.")
        return cast(dict[str, Any], data[0])

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }

    def _database_headers(self, access_token: str) -> dict[str, str]:
        if not self.supabase_anon_key or not access_token:
            raise DocumentServiceError("Supabase document database access is not configured.")

        return {
            "apikey": self.supabase_anon_key,
            "Authorization": f"Bearer {access_token}",
        }

    def _require_supabase_config(self) -> None:
        if not self.supabase_url or not self.service_role_key:
            raise DocumentServiceError("Supabase document storage is not configured.")

    @staticmethod
    def _raise_for_supabase_error(response: httpx.Response, message: str) -> None:
        if response.status_code >= 400:
            error_body = response.text
            logger.warning(
                "Supabase REST error: status_code=%s path=%s body=%s",
                response.status_code,
                response.request.url.path,
                error_body,
            )
            raise DocumentServiceError(message, status_code=response.status_code, body=error_body)

    @staticmethod
    def _storage_path(*, user_id: UUID, file_hash: str, filename: str) -> str:
        safe_filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
        if not safe_filename:
            safe_filename = "upload"
        return f"{user_id}/{file_hash}/{safe_filename}"

    @staticmethod
    def _summary_from_row(row: dict[str, Any]) -> DocumentSummary:
        document_id = row.get("id")
        filename = row.get("filename")
        status = row.get("status")
        created_at = row.get("created_at")
        summary = row.get("summary")
        metadata = row.get("metadata")

        if not isinstance(document_id, str):
            raise DocumentServiceError("Document row is missing id.")
        if not isinstance(filename, str):
            raise DocumentServiceError("Document row is missing filename.")
        if status not in {"pending", "ingesting", "processing", "ready", "completed", "failed"}:
            raise DocumentServiceError("Document row has invalid status.")
        if not isinstance(created_at, str):
            raise DocumentServiceError("Document row is missing created_at.")

        return DocumentSummary(
            id=UUID(document_id),
            filename=filename,
            status=cast(DocumentStatus, status),
            created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00")),
            summary=summary if isinstance(summary, str) else None,
            metadata=metadata if isinstance(metadata, dict) and metadata else None,
        )
