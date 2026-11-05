from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str | None = None
    access_token: str = ""


def _unauthorized(detail: str = "Invalid or missing authentication token.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _get_string(value: dict[str, Any], key: str) -> str | None:
    raw_value = value.get(key)
    return raw_value if isinstance(raw_value, str) else None


class SupabaseAuthVerifier:
    def __init__(
        self,
        supabase_url: str,
        supabase_anon_key: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.supabase_anon_key = supabase_anon_key
        self.timeout_seconds = timeout_seconds

    async def verify_token(self, access_token: str) -> CurrentUser:
        if not self.supabase_url or not self.supabase_anon_key:
            raise _unauthorized("Supabase authentication is not configured.")

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{self.supabase_url}/auth/v1/user",
                    headers={
                        "apikey": self.supabase_anon_key,
                        "Authorization": f"Bearer {access_token}",
                    },
                )
        except httpx.HTTPError as exc:
            raise _unauthorized() from exc

        if response.status_code != status.HTTP_200_OK:
            raise _unauthorized()

        try:
            payload = response.json()
        except ValueError as exc:
            raise _unauthorized() from exc

        if not isinstance(payload, dict):
            raise _unauthorized()

        user_id = _get_string(payload, "id")
        if user_id is None:
            raise _unauthorized()

        try:
            parsed_user_id = UUID(user_id)
        except ValueError as exc:
            raise _unauthorized() from exc

        return CurrentUser(
            id=parsed_user_id,
            email=_get_string(payload, "email"),
            access_token=access_token,
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    if credentials is None:
        raise _unauthorized()

    settings = get_settings()
    verifier = SupabaseAuthVerifier(
        supabase_url=settings.supabase_url,
        supabase_anon_key=settings.supabase_anon_key,
    )
    return await verifier.verify_token(credentials.credentials)
