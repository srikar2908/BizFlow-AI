from uuid import UUID

from pydantic import BaseModel


class CurrentUserResponse(BaseModel):
    user_id: UUID
    email: str | None = None
