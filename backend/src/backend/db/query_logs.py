"""Insert rows into query_logs."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Json


def insert_query_log(
    conn: psycopg.Connection,
    *,
    notebook_id: int,
    question: str,
    retrieved_chunk_ids: list[int],
    scores: list[float],
    answer: str,
    citations: dict[str, Any],
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
) -> int:
    """Insert one query log row. Returns the new row id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO query_logs (
                notebook_id,
                question,
                retrieved_chunk_ids,
                scores,
                answer,
                citations,
                model,
                prompt_tokens,
                completion_tokens,
                latency_ms
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                notebook_id,
                question,
                retrieved_chunk_ids,
                scores,
                answer,
                Json(citations),
                model,
                prompt_tokens,
                completion_tokens,
                latency_ms,
            ),
        )
        row = cur.fetchone()
    assert row is not None
    return row[0]
