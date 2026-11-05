from uuid import UUID

from fastapi.testclient import TestClient

from app.api.routes_rag import get_rag_answer_service, get_rag_search_service
from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.schemas.rag import RagAnswerResponse, RagCitation, RagSearchResult

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000201")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000101")


class FakeRagSearchService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def search(
        self,
        *,
        query: str,
        match_count: int,
        user_id: UUID,
        access_token: str,
    ) -> list[RagSearchResult]:
        self.calls.append(
            {
                "query": query,
                "match_count": match_count,
                "user_id": user_id,
                "access_token": access_token,
            }
        )
        return [
            RagSearchResult(
                chunk_id=CHUNK_ID,
                document_id=DOCUMENT_ID,
                filename="bizflow-test.txt",
                chunk_index=0,
                content="This is a BizFlow AI test document.",
                similarity=0.91,
            )
        ]


class FakeRagAnswerService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def answer(
        self,
        *,
        query: str,
        match_count: int,
        current_user: CurrentUser,
    ) -> RagAnswerResponse:
        self.calls.append(
            {
                "query": query,
                "match_count": match_count,
                "current_user": current_user,
            }
        )
        return RagAnswerResponse(
            answer="The document says this is a BizFlow AI test document.",
            citations=[
                RagCitation(
                    document_id=DOCUMENT_ID,
                    filename="bizflow-test.txt",
                    chunk_index=0,
                    preview="This is a BizFlow AI test document.",
                )
            ],
        )


def override_user() -> CurrentUser:
    return CurrentUser(
        id=USER_ID,
        email="owner@example.com",
        access_token="test-access-token",
    )


def test_rag_search_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post("/rag/search", json={"query": "proposal"})

    assert response.status_code == 401


def test_rag_search_rejects_empty_query() -> None:
    app.dependency_overrides[get_current_user] = override_user
    client = TestClient(app)

    try:
        response = client.post("/rag/search", json={"query": "   "})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_rag_search_returns_user_scoped_results() -> None:
    service = FakeRagSearchService()
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_rag_search_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/rag/search", json={"query": "test document", "match_count": 3})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "chunk_id": str(CHUNK_ID),
                "document_id": str(DOCUMENT_ID),
                "filename": "bizflow-test.txt",
                "chunk_index": 0,
                "content": "This is a BizFlow AI test document.",
                "similarity": 0.91,
            }
        ]
    }
    assert service.calls == [
        {
            "query": "test document",
            "match_count": 3,
            "user_id": USER_ID,
            "access_token": "test-access-token",
        }
    ]


def test_rag_answer_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.post("/rag/answer", json={"query": "proposal"})

    assert response.status_code == 401


def test_rag_answer_rejects_empty_query() -> None:
    app.dependency_overrides[get_current_user] = override_user
    client = TestClient(app)

    try:
        response = client.post("/rag/answer", json={"query": "   "})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_rag_answer_returns_answer_and_citations() -> None:
    service = FakeRagAnswerService()
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_rag_answer_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/rag/answer", json={"query": "test document", "match_count": 3})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "answer": "The document says this is a BizFlow AI test document.",
        "citations": [
            {
                "document_id": str(DOCUMENT_ID),
                "filename": "bizflow-test.txt",
                "chunk_index": 0,
                "preview": "This is a BizFlow AI test document.",
            }
        ],
    }
    assert service.calls == [
        {
            "query": "test document",
            "match_count": 3,
            "current_user": override_user(),
        }
    ]
