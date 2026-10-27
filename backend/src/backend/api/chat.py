"""POST /notebooks/{notebook_id}/chat — grounded Q&A with citations."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
import psycopg

from backend.api.dependencies import get_chat_provider, get_db, get_embedder
from backend.llm.base import ChatProvider, EmbeddingProvider, LLMError
from backend.services import answering as answering_service
from backend.services.errors import NotebookNotFoundError, QueryLogInsertError

router = APIRouter(prefix="/notebooks/{notebook_id}", tags=["chat"])


class ChatRequest(BaseModel):
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


class SourceChunkOut(BaseModel):
    label: int
    chunk_id: int
    document_id: int
    filename: str
    page_number: int
    chunk_index: int
    score: float
    text: str
    cited: bool


class ChatResponse(BaseModel):
    question: str
    answer: str
    answered: bool
    citations: list[int]
    sources: list[SourceChunkOut]


@router.post("/chat", response_model=ChatResponse)
def chat(
    notebook_id: int,
    body: ChatRequest,
    conn: psycopg.Connection = Depends(get_db),
    embedder: EmbeddingProvider = Depends(get_embedder),
    chat_provider: ChatProvider = Depends(get_chat_provider),
) -> ChatResponse:
    try:
        result = answering_service.answer_question(
            conn,
            notebook_id,
            body.question,
            embedder=embedder,
            chat_provider=chat_provider,
            k=body.k,
        )
    except NotebookNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found",
        ) from None
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM service error: {exc}",
        ) from None
    except QueryLogInsertError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist query log",
        ) from None

    return ChatResponse(
        question=result.question,
        answer=result.answer,
        answered=result.answered,
        citations=result.citations,
        sources=[
            SourceChunkOut(
                label=s.label,
                chunk_id=s.chunk_id,
                document_id=s.document_id,
                filename=s.filename,
                page_number=s.page_number,
                chunk_index=s.chunk_index,
                score=s.score,
                text=s.text,
                cited=s.cited,
            )
            for s in result.sources
        ],
    )
