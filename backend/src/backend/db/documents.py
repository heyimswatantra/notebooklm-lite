from dataclasses import dataclass
from datetime import datetime

import psycopg

from backend.rag.chunking import Chunk


@dataclass(frozen=True)
class Document:
    id: int
    notebook_id: int
    filename: str
    page_count: int
    created_at: datetime


@dataclass(frozen=True)
class DocumentSummary:
    id: int
    filename: str
    page_count: int
    chunk_count: int
    created_at: datetime


def insert_document(
    conn: psycopg.Connection,
    notebook_id: int,
    filename: str,
    page_count: int,
) -> Document:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (notebook_id, filename, page_count)
            VALUES (%s, %s, %s)
            RETURNING id, notebook_id, filename, page_count, created_at;
            """,
            (notebook_id, filename, page_count),
        )
        row = cur.fetchone()
        assert row is not None
        return Document(
            id=row[0],
            notebook_id=row[1],
            filename=row[2],
            page_count=row[3],
            created_at=row[4],
        )


def insert_chunks(
    conn: psycopg.Connection,
    document_id: int,
    chunks: list[Chunk],
    vectors: list[list[float]],
    embedding_model: str,
) -> None:
    if len(chunks) != len(vectors):
        raise ValueError(
            f"chunk/vector count mismatch: {len(chunks)} chunks, {len(vectors)} vectors"
        )
    rows = [
        (
            document_id,
            chunk.chunk_index,
            chunk.page_number,
            chunk.text,
            vector,
            embedding_model,
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO chunks (
                document_id, chunk_index, page_number, text, embedding, embedding_model
            )
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            rows,
        )


def list_documents(conn: psycopg.Connection, notebook_id: int) -> list[DocumentSummary]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT d.id, d.filename, d.page_count, COUNT(c.id) AS chunk_count, d.created_at
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            WHERE d.notebook_id = %s
            GROUP BY d.id
            ORDER BY d.created_at;
            """,
            (notebook_id,),
        )
        rows = cur.fetchall()
        return [
            DocumentSummary(
                id=r[0],
                filename=r[1],
                page_count=r[2],
                chunk_count=r[3],
                created_at=r[4],
            )
            for r in rows
        ]

