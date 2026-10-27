"""Shared test helpers for DB and vector fixtures."""

from __future__ import annotations

import psycopg
from fastapi.testclient import TestClient

from backend.db.documents import insert_chunks, insert_document
from backend.db.notebooks import create_notebook
from backend.rag.chunking import Chunk

DIM = 1024


def unit_vector(axis: int, dim: int = DIM) -> list[float]:
    """Return a unit vector with 1.0 at *axis* and 0.0 elsewhere."""
    v = [0.0] * dim
    v[axis] = 1.0
    return v


def setup_notebook_with_chunks(
    conn: psycopg.Connection,
    vectors: list[list[float]],
    *,
    notebook_name: str = "test-nb",
    filename: str = "doc.pdf",
) -> tuple[int, int]:
    """Insert a notebook, document, and chunks. Returns ``(notebook_id, document_id)``."""
    nb = create_notebook(conn, notebook_name)
    doc = insert_document(conn, nb.id, filename, page_count=1)
    chunks = [
        Chunk(text=f"chunk-{i}", page_number=1, chunk_index=i, token_count=5)
        for i in range(len(vectors))
    ]
    insert_chunks(conn, doc.id, chunks, vectors, "fake-embed-model")
    conn.commit()
    return nb.id, doc.id


def create_notebook_via_api(client: TestClient, name: str = "Test NB") -> int:
    resp = client.post("/notebooks", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]
