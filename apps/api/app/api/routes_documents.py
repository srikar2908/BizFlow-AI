from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.schemas.documents import (
    DocumentEmailDraftResponse,
    DocumentIngestResponse,
    DocumentMetadataResponse,
    DocumentProposalResponse,
    DocumentSummary,
    DocumentSummaryResponse,
    DocumentUploadResponse,
)
from app.services.document_email_draft_service import (
    DocumentEmailDraftService,
    DocumentEmailDraftServiceError,
)
from app.services.document_metadata_service import (
    DocumentMetadataService,
    DocumentMetadataServiceError,
)
from app.services.document_proposal_service import (
    DocumentProposalService,
    DocumentProposalServiceError,
)
from app.services.document_service import DocumentService, DocumentServiceError
from app.services.document_summary_service import (
    DocumentSummaryService,
    DocumentSummaryServiceError,
)
from app.services.ingestion_service import IngestionService, IngestionServiceError

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}


def get_document_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentService:
    return DocumentService(settings)


def get_ingestion_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestionService:
    return IngestionService(settings)


def get_metadata_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentMetadataService:
    return DocumentMetadataService(settings)


def get_summary_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentSummaryService:
    return DocumentSummaryService(settings)


def get_proposal_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentProposalService:
    return DocumentProposalService(settings)


def get_email_draft_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentEmailDraftService:
    return DocumentEmailDraftService(settings)


def _file_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return f".{filename.rsplit('.', 1)[-1].lower()}"


def _validate_filename(filename: str | None) -> str:
    if filename is None or not filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a filename.",
        )

    clean_filename = filename.strip()
    if _file_extension(clean_filename) not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed types: pdf, docx, txt, md, csv.",
        )

    return clean_filename


@router.get("", response_model=list[DocumentSummary], response_model_exclude_none=True)
async def list_documents(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> list[DocumentSummary]:
    try:
        return await service.list_documents_for_user(
            user_id=current_user.id,
            access_token=current_user.access_token,
        )
    except DocumentServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/{document_id}/ingest", response_model=DocumentIngestResponse)
async def ingest_document(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> DocumentIngestResponse:
    try:
        result = await service.ingest_document(
            document_id=document_id,
            user_id=current_user.id,
            access_token=current_user.access_token,
        )
    except IngestionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return DocumentIngestResponse(
        id=result.document_id,
        status="completed",
        chunks_created=result.chunks_created,
    )


@router.post("/{document_id}/metadata", response_model=DocumentMetadataResponse)
async def extract_document_metadata(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[DocumentMetadataService, Depends(get_metadata_service)],
) -> DocumentMetadataResponse:
    try:
        return await service.extract_metadata(
            document_id=document_id,
            user_id=current_user.id,
            access_token=current_user.access_token,
        )
    except DocumentMetadataServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{document_id}/summary", response_model=DocumentSummaryResponse)
async def generate_document_summary(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[DocumentSummaryService, Depends(get_summary_service)],
) -> DocumentSummaryResponse:
    try:
        return await service.generate_summary(
            document_id=document_id,
            user_id=current_user.id,
            access_token=current_user.access_token,
        )
    except DocumentSummaryServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{document_id}/proposal", response_model=DocumentProposalResponse)
async def generate_document_proposal(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[DocumentProposalService, Depends(get_proposal_service)],
) -> DocumentProposalResponse:
    try:
        return await service.generate_proposal(
            document_id=document_id,
            user_id=current_user.id,
            access_token=current_user.access_token,
        )
    except DocumentProposalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{document_id}/email-draft", response_model=DocumentEmailDraftResponse)
async def generate_document_email_draft(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[DocumentEmailDraftService, Depends(get_email_draft_service)],
) -> DocumentEmailDraftResponse:
    try:
        return await service.generate_email_draft(
            document_id=document_id,
            user_id=current_user.id,
            access_token=current_user.access_token,
        )
    except DocumentEmailDraftServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File(...)],
) -> DocumentUploadResponse:
    filename = _validate_filename(file.filename)
    content = await file.read()

    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Uploaded file exceeds the {settings.max_upload_bytes} byte limit.",
        )

    try:
        return await service.upload_document(
            user_id=current_user.id,
            access_token=current_user.access_token,
            filename=filename,
            mime_type=file.content_type,
            content=content,
        )
    except DocumentServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
