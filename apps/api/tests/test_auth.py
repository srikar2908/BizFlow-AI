from uuid import UUID

from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.main import app


def test_me_rejects_missing_token() -> None:
    client = TestClient(app)

    response = client.get("/me")

    assert response.status_code == 401


def test_me_auth_dependency_can_be_overridden() -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="owner@example.com",
    )
    client = TestClient(app)

    try:
        response = client.get("/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "email": "owner@example.com",
    }
