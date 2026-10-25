"""POST /notebooks/{notebook_id}/retrieve — vector similarity search endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
import psycopg

from backend.api.dependencies import get_db, get_embedder
from backend.llm.base import EmbeddingProvider, LLMError
from backend.services import retrieval as retrieval_service
from backend.services.errors import NotebookNotFoundError

router = APIRouter(prefix="/notebooks/{notebook_id}", tags=["retrieval"])


# --- request / response models ---------------------------------------------------


class RetrieveRequest(BaseModel):
    question: str
    k: int = Field(default=5, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Question cannot be empty")
        if len(stripped) > 2000:
            raise ValueError("Question cannot exceed 2000 characters")
        return stripped


class ChunkHit(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    page_number: int
    chunk_index: int
    score: float
    text: str


class RetrieveResponse(BaseModel):
    question: str
    k: int
    chunks: list[ChunkHit]


# --- endpoint ---------------------------------------------------------------------


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(
    notebook_id: int,
    body: RetrieveRequest,
    conn: psycopg.Connection = Depends(get_db),
    embedder: EmbeddingProvider = Depends(get_embedder),
) -> RetrieveResponse:
    try:
        results = retrieval_service.retrieve_chunks(
            conn,
            notebook_id,
            body.question,
            embedder=embedder,
            k=body.k,
        )
        print(results)
    except NotebookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found",
        ) from None
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding service error: {exc}",
        ) from None

    return RetrieveResponse(
        question=body.question,
        k=body.k,
        chunks=[
            ChunkHit(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                filename=c.filename,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                score=c.score,
                text=c.text,
            )
            for c in results
        ],
    )
