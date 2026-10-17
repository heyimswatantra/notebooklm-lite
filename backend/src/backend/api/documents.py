import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
import psycopg

from backend.config import get_settings
from backend.db.connection import get_db
from backend.llm.base import EmbeddingProvider, LLMError
from backend.llm.factory import get_embedding_provider
from backend.rag.extraction import CorruptPdfError, NoExtractableTextError
from backend.db.documents import DocumentSummary
from backend.services import ingestion as ingestion_service
from backend.services.ingestion import NotebookNotFoundError

router = APIRouter(prefix="/notebooks/{notebook_id}/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def get_embedder() -> EmbeddingProvider:
    """FastAPI dependency — configured embedding provider (sole api/ → llm/ touchpoint)."""
    return get_embedding_provider(get_settings())


class DocumentResponse(BaseModel):
    id: int
    filename: str
    page_count: int
    chunk_count: int
    created_at: datetime


def _document_response(summary: DocumentSummary) -> DocumentResponse:
    return DocumentResponse(
        id=summary.id,
        filename=summary.filename,
        page_count=summary.page_count,
        chunk_count=summary.chunk_count,
        created_at=summary.created_at,
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    notebook_id: int,
    file: UploadFile,
    conn: psycopg.Connection = Depends(get_db),
    embedder: EmbeddingProvider = Depends(get_embedder),
) -> DocumentResponse:
    raw_name = file.filename or "upload.pdf"
    filename = os.path.basename(raw_name)

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted",
        )

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File exceeds 20 MB limit",
        )

    if len(data) < 5 or data[:5] != b"%PDF-":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a valid PDF",
        )

    try:
        summary = ingestion_service.ingest_document(
            conn,
            notebook_id,
            filename,
            data,
            embedder=embedder,
        )
    except NotebookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found",
        ) from None
    except CorruptPdfError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a valid PDF",
        ) from None
    except NoExtractableTextError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No extractable text in PDF",
        ) from None
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding service error: {exc}",
        ) from None

    return _document_response(summary)


@router.get("", response_model=list[DocumentResponse])
def get_documents(
    notebook_id: int,
    conn: psycopg.Connection = Depends(get_db),
) -> list[DocumentResponse]:
    try:
        summaries = ingestion_service.list_documents(conn, notebook_id)
    except NotebookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found",
        ) from None

    return [_document_response(s) for s in summaries]
