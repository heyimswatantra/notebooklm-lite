"""Vector similarity search over chunks.

search_chunks() finds the top-k chunks closest to a query vector within a
single notebook, using pgvector's cosine-distance operator (<=>).
"""

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned by vector similarity search."""

    chunk_id: int
    document_id: int
    filename: str
    page_number: int
    chunk_index: int
    score: float
    text: str


def search_chunks(
    conn: psycopg.Connection,
    notebook_id: int,
    query_vector: list[float],
    k: int,
) -> list[RetrievedChunk]:
    """Return the *k* chunks nearest to *query_vector* in the given notebook.

    Uses pgvector cosine distance (``<=>``) for ranking.
    ``score = 1 - distance`` so identical vectors score ≈ 1.0 and
    orthogonal vectors score ≈ 0.0.

    Results are ordered by distance ascending (best first), with ties
    broken by chunk id ascending.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id,
                   c.document_id,
                   d.filename,
                   c.page_number,
                   c.chunk_index,
                   (c.embedding <=> %s::vector) AS distance,
                   c.text
              FROM chunks c
              JOIN documents d ON d.id = c.document_id
             WHERE d.notebook_id = %s
             ORDER BY distance ASC, c.id ASC
             LIMIT %s;
            """,
            (query_vector, notebook_id, k),
        )
        rows = cur.fetchall()

    return [
        RetrievedChunk(
            chunk_id=row[0],
            document_id=row[1],
            filename=row[2],
            page_number=row[3],
            chunk_index=row[4],
            score=1.0 - row[5],  # score = 1 - distance
            text=row[6],
        )
        for row in rows
    ]
