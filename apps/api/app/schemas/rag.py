from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    match_count: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError("Query must not be empty.")
        return clean_value


class RagSearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    filename: str
    chunk_index: int
    content: str
    similarity: float


class RagSearchResponse(BaseModel):
    results: list[RagSearchResult]


class RagAnswerRequest(RagSearchRequest):
    pass


class RagCitation(BaseModel):
    document_id: UUID
    filename: str
    chunk_index: int
    preview: str


class RagAnswerResponse(BaseModel):
    answer: str
    citations: list[RagCitation]
