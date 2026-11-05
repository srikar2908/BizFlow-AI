from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.routes_auth import router as auth_router
from app.api.routes_documents import router as documents_router
from app.api.routes_rag import router as rag_router
from app.api.routes_workflows import router as workflows_router
from app.core.config import get_settings

LOCAL_CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


def get_cors_origins(configured_origins: list[str]) -> list[str]:
    return list(dict.fromkeys([*configured_origins, *LOCAL_CORS_ORIGINS]))


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(rag_router)
    app.include_router(workflows_router)
    return app


app = create_app()
