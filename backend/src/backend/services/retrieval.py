"""Retrieval service: embed a question and find the most relevant chunks."""

import logging
import time

import psycopg

from backend.db.chunks import RetrievedChunk, search_chunks
from backend.db.notebooks import notebook_exists
from backend.llm.base import EmbeddingProvider
from backend.services.errors import NotebookNotFoundError

logger = logging.getLogger(__name__)


def retrieve_chunks(
    conn: psycopg.Connection,
    notebook_id: int,
    question: str,
    *,
    embedder: EmbeddingProvider,
    k: int = 5,
) -> list[RetrievedChunk]:
    """Embed *question* and return the top-*k* chunks from the notebook.

    Raises ``NotebookNotFoundError`` if the notebook does not exist.
    """
    if not notebook_exists(conn, notebook_id):
        raise NotebookNotFoundError(notebook_id)

    # --- embed the question ---
    embed_start = time.perf_counter()
    embed_result = embedder.embed([question], kind="query")
    embed_seconds = time.perf_counter() - embed_start
    query_vector = embed_result.vectors[0]

    # --- vector search ---
    search_start = time.perf_counter()
    chunks = search_chunks(conn, notebook_id, query_vector, k)
    search_seconds = time.perf_counter() - search_start

    logger.info(
        "retrieve notebook_id=%s question=%r chunk_ids=%s scores=%s "
        "embed_s=%.3f search_s=%.3f",
        notebook_id,
        question,
        [c.chunk_id for c in chunks],
        [round(c.score, 4) for c in chunks],
        embed_seconds,
        search_seconds,
    )

    return chunks
