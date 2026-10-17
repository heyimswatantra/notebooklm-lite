import logging
import time

import psycopg

from backend.db import documents as db_documents
from backend.db.documents import DocumentSummary
from backend.db.notebooks import notebook_exists
from backend.llm.base import EmbeddingProvider
from backend.rag.chunking import chunk_pages
from backend.rag.extraction import extract_pages

logger = logging.getLogger(__name__)


class NotebookNotFoundError(Exception):
    """Raised when the target notebook does not exist."""


def ingest_document(
    conn: psycopg.Connection,
    notebook_id: int,
    filename: str,
    pdf_bytes: bytes,
    *,
    embedder: EmbeddingProvider,
) -> DocumentSummary:
    if not notebook_exists(conn, notebook_id):
        raise NotebookNotFoundError(notebook_id)

    pages = extract_pages(pdf_bytes)
    chunks = chunk_pages(pages)

    texts = [c.text for c in chunks]
    embed_start = time.perf_counter()
    embed_result = embedder.embed(texts, kind="document")
    embed_seconds = time.perf_counter() - embed_start

    doc = db_documents.insert_document(
        conn, notebook_id, filename, page_count=len(pages)
    )
    db_documents.insert_chunks(
        conn, doc.id, chunks, embed_result.vectors, embed_result.model
    )

    logger.info(
        "Ingested document id=%s pages=%s chunks=%s model=%s dim=%s vectors=%s embed_s=%.3f",
        doc.id,
        len(pages),
        len(chunks),
        embed_result.model,
        embed_result.dimension,
        len(embed_result.vectors),
        embed_seconds,
    )

    return DocumentSummary(
        id=doc.id,
        filename=doc.filename,
        page_count=doc.page_count,
        chunk_count=len(chunks),
        created_at=doc.created_at,
    )


def list_documents(
    conn: psycopg.Connection,
    notebook_id: int,
) -> list[DocumentSummary]:
    if not notebook_exists(conn, notebook_id):
        raise NotebookNotFoundError(notebook_id)
    return db_documents.list_documents(conn, notebook_id)
