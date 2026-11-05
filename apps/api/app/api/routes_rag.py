import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.schemas.rag import RagAnswerRequest, RagAnswerResponse, RagSearchRequest, RagSearchResponse
from app.services.generation_service import GenerationService
from app.services.rag_answer_service import RagAnswerService, RagAnswerServiceError
from app.services.rag_search_service import RagSearchService, RagSearchServiceError

router = APIRouter(prefix="/rag", tags=["rag"])
logger = logging.getLogger(__name__)


def get_rag_search_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RagSearchService:
    return RagSearchService(settings)


def get_rag_answer_service(
    search_service: Annotated[RagSearchService, Depends(get_rag_search_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RagAnswerService:
    return RagAnswerService(
        search_service=search_service,
        generation_service=GenerationService(settings),
    )


@router.post("/search", response_model=RagSearchResponse)
async def search_rag(
    request: RagSearchRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[RagSearchService, Depends(get_rag_search_service)],
) -> RagSearchResponse:
    try:
        results = await service.search(
            query=request.query,
            match_count=request.match_count,
            user_id=current_user.id,
            access_token=current_user.access_token,
        )
    except RagSearchServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return RagSearchResponse(results=results)


@router.post("/answer", response_model=RagAnswerResponse)
async def answer_rag(
    request: RagAnswerRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[RagAnswerService, Depends(get_rag_answer_service)],
) -> RagAnswerResponse:
    logger.info("Received RAG answer request: query_length=%s", len(request.query))
    try:
        return await service.answer(
            query=request.query,
            match_count=request.match_count,
            current_user=current_user,
        )
    except RagAnswerServiceError as exc:
        logger.warning(
            "RAG answer request failed: query_length=%s exception_type=%s message=%s",
            len(request.query),
            type(exc).__name__,
            str(exc),
        )
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
