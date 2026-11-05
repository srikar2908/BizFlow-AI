from fastapi.testclient import TestClient

from app.main import app


def test_local_frontend_origin_can_preflight_rag_search() -> None:
    client = TestClient(app)

    response = client.options(
        "/rag/search",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_loopback_frontend_origin_can_preflight_rag_search() -> None:
    client = TestClient(app)

    response = client.options(
        "/rag/search",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert response.headers["access-control-allow-credentials"] == "true"
