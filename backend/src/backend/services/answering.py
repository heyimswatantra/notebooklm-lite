"""Answer questions with retrieval, grounded generation, and query logging."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import psycopg

from backend.db.chunks import RetrievedChunk
from backend.db.query_logs import insert_query_log
from backend.llm.base import ChatProvider, EmbeddingProvider
from backend.rag.citations import parse_citations
from backend.rag.prompting import NOT_FOUND_MESSAGE, PROMPT_VERSION, build_messages
from backend.services import retrieval as retrieval_service
from backend.services.errors import QueryLogInsertError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceChunk:
    label: int
    chunk_id: int
    document_id: int
    filename: str
    page_number: int
    chunk_index: int
    score: float
    text: str
    cited: bool


@dataclass(frozen=True)
class Answer:
    question: str
    answer: str
    answered: bool
    citations: list[int]
    sources: list[SourceChunk]
    latency_ms: int


def _sources_from_chunks(
    chunks: list[RetrievedChunk],
    cited_labels: set[int],
) -> list[SourceChunk]:
    return [
        SourceChunk(
            label=i,
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            filename=c.filename,
            page_number=c.page_number,
            chunk_index=c.chunk_index,
            score=c.score,
            text=c.text,
            cited=i in cited_labels,
        )
        for i, c in enumerate(chunks, start=1)
    ]


def _citations_jsonb(
    cited_labels: list[int],
    label_to_chunk_id: dict[int, int],
    invalid_labels: list[int],
) -> dict[str, object]:
    return {
        "cited": [
            {"label": label, "chunk_id": label_to_chunk_id[label]}
            for label in cited_labels
        ],
        "invalid_labels": invalid_labels,
    }


def _persist_log(
    conn: psycopg.Connection,
    *,
    notebook_id: int,
    question: str,
    chunks: list[RetrievedChunk],
    answer_text: str,
    citations_payload: dict[str, object],
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
) -> None:
    try:
        insert_query_log(
            conn,
            notebook_id=notebook_id,
            question=question,
            retrieved_chunk_ids=[c.chunk_id for c in chunks],
            scores=[c.score for c in chunks],
            answer=answer_text,
            citations=citations_payload,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise QueryLogInsertError("Failed to write query log") from exc


def answer_question(
    conn: psycopg.Connection,
    notebook_id: int,
    question: str,
    *,
    embedder: EmbeddingProvider,
    chat_provider: ChatProvider,
    k: int = 5,
) -> Answer:
    """Retrieve context, generate an answer, parse citations, and log the query."""
    start = time.perf_counter()

    retrieve_start = time.perf_counter()
    chunks = retrieval_service.retrieve_chunks(
        conn,
        notebook_id,
        question,
        embedder=embedder,
        k=k,
    )
    retrieve_ms = (time.perf_counter() - retrieve_start) * 1000

    if not chunks:
        answer_text = NOT_FOUND_MESSAGE
        answered = False
        cited_labels: list[int] = []
        invalid_labels: list[int] = []
        label_to_chunk_id: dict[int, int] = {}
        model = "none"
        prompt_tokens = 0
        completion_tokens = 0
        chat_ms = 0.0

        latency_ms = int((time.perf_counter() - start) * 1000)
        citations_payload = _citations_jsonb(cited_labels, label_to_chunk_id, invalid_labels)

        logger.info(
            "answer notebook_id=%s prompt_version=%s retrieve_ms=%.1f chat_ms=%.1f "
            "latency_ms=%s answered=%s chunk_ids=%s",
            notebook_id,
            PROMPT_VERSION,
            retrieve_ms,
            chat_ms,
            latency_ms,
            answered,
            [],
        )

        _persist_log(
            conn,
            notebook_id=notebook_id,
            question=question,
            chunks=chunks,
            answer_text=answer_text,
            citations_payload=citations_payload,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )

        return Answer(
            question=question,
            answer=answer_text,
            answered=answered,
            citations=cited_labels,
            sources=[],
            latency_ms=latency_ms,
        )

    built = build_messages(question, chunks)
    label_to_chunk_id = built.label_to_chunk_id
    valid_labels = set(label_to_chunk_id.keys())

    chat_start = time.perf_counter()
    chat_result = chat_provider.chat(built.messages)
    chat_ms = (time.perf_counter() - chat_start) * 1000

    answer_text = chat_result.text
    stripped = answer_text.strip()

    if stripped == NOT_FOUND_MESSAGE:
        answered = False
        cited_labels = []
        invalid_labels: list[int] = []
    else:
        if NOT_FOUND_MESSAGE in answer_text:
            logger.warning(
                "answer contains NOT_FOUND_MESSAGE but is not an exact match "
                "notebook_id=%s prompt_version=%s",
                notebook_id,
                PROMPT_VERSION,
            )
        parsed = parse_citations(answer_text, valid_labels)
        cited_labels = parsed.cited_labels
        invalid_labels = parsed.invalid_labels
        answered = True

        if invalid_labels:
            logger.info(
                "invalid citation labels notebook_id=%s labels=%s prompt_version=%s",
                notebook_id,
                invalid_labels,
                PROMPT_VERSION,
            )

        if not cited_labels:
            logger.warning(
                "answer has no valid citations notebook_id=%s prompt_version=%s",
                notebook_id,
                PROMPT_VERSION,
            )

    citations_payload = _citations_jsonb(cited_labels, label_to_chunk_id, invalid_labels)
    latency_ms = int((time.perf_counter() - start) * 1000)

    logger.info(
        "answer notebook_id=%s prompt_version=%s retrieve_ms=%.1f chat_ms=%.1f "
        "latency_ms=%s answered=%s chunk_ids=%s model=%s",
        notebook_id,
        PROMPT_VERSION,
        retrieve_ms,
        chat_ms,
        latency_ms,
        answered,
        [c.chunk_id for c in chunks],
        chat_result.model,
    )

    _persist_log(
        conn,
        notebook_id=notebook_id,
        question=question,
        chunks=chunks,
        answer_text=answer_text,
        citations_payload=citations_payload,
        model=chat_result.model,
        prompt_tokens=chat_result.prompt_tokens,
        completion_tokens=chat_result.completion_tokens,
        latency_ms=latency_ms,
    )

    cited_set = set(cited_labels)
    return Answer(
        question=question,
        answer=answer_text,
        answered=answered,
        citations=cited_labels,
        sources=_sources_from_chunks(chunks, cited_set),
        latency_ms=latency_ms,
    )
