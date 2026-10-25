"""Tests for M4 retrieval: db/chunks.py, services/retrieval.py, api/retrieve.py."""

from __future__ import annotations

import math
from typing import Literal

import psycopg
import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_embedder
from backend.db.chunks import RetrievedChunk, search_chunks
from backend.db.documents import insert_chunks, insert_document
from backend.db.notebooks import create_notebook
from backend.llm.base import EmbedResult, LLMError
from backend.main import app
from backend.services import retrieval as retrieval_service
from backend.services.errors import NotebookNotFoundError
from tests.fakes import FakeEmbeddingProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DIM = 1024


def _unit_vector(axis: int, dim: int = DIM) -> list[float]:
    """Return a unit vector with 1.0 at *axis* and 0.0 elsewhere."""
    v = [0.0] * dim
    v[axis] = 1.0
    return v


def _setup_notebook_with_chunks(
    conn: psycopg.Connection,
    vectors: list[list[float]],
    *,
    notebook_name: str = "test-nb",
    filename: str = "doc.pdf",
) -> tuple[int, int]:
    """Insert a notebook, document, and chunks with the given vectors.

    Each chunk gets a trivial text, chunk_index equal to its position,
    and page_number = 1.  Returns ``(notebook_id, document_id)``.
    """
    from backend.rag.chunking import Chunk

    nb = create_notebook(conn, notebook_name)
    doc = insert_document(conn, nb.id, filename, page_count=1)
    chunks = [
        Chunk(text=f"chunk-{i}", page_number=1, chunk_index=i, token_count=5)
        for i in range(len(vectors))
    ]
    insert_chunks(conn, doc.id, chunks, vectors, "fake-embed-model")
    conn.commit()
    return nb.id, doc.id


# ---------------------------------------------------------------------------
# db/chunks.py  — search_chunks
# ---------------------------------------------------------------------------


class TestSearchChunks:
    """Low-level tests against the real test database."""

    def test_ordering_by_similarity(self, db_conn: psycopg.Connection) -> None:
        """Identical vector → score ≈ 1.0; orthogonal → score ≈ 0.0; ordered descending."""
        v0 = _unit_vector(0)
        v1 = _unit_vector(1)
        v2 = _unit_vector(2)
        nb_id, _ = _setup_notebook_with_chunks(db_conn, [v0, v1, v2])

        results = search_chunks(db_conn, nb_id, v0, k=10)

        assert len(results) == 3
        # First result is the identical vector (axis-0)
        assert results[0].chunk_index == 0
        assert results[0].score == pytest.approx(1.0, abs=1e-6)
        # Other two are orthogonal
        assert results[1].score == pytest.approx(0.0, abs=1e-6)
        assert results[2].score == pytest.approx(0.0, abs=1e-6)
        # Scores are descending (distance ascending)
        assert results[0].score >= results[1].score >= results[2].score

    def test_k_limits_results(self, db_conn: psycopg.Connection) -> None:
        v0, v1, v2 = _unit_vector(0), _unit_vector(1), _unit_vector(2)
        nb_id, _ = _setup_notebook_with_chunks(db_conn, [v0, v1, v2])

        results = search_chunks(db_conn, nb_id, v0, k=2)
        assert len(results) == 2

    def test_k_greater_than_available(self, db_conn: psycopg.Connection) -> None:
        """k exceeds available chunks → returns all available."""
        v0 = _unit_vector(0)
        nb_id, _ = _setup_notebook_with_chunks(db_conn, [v0])

        results = search_chunks(db_conn, nb_id, v0, k=20)
        assert len(results) == 1
        assert results[0].score == pytest.approx(1.0, abs=1e-6)

    def test_notebook_isolation(self, db_conn: psycopg.Connection) -> None:
        """Chunks from another notebook are never returned."""
        shared_vec = _unit_vector(0)
        nb_a, _ = _setup_notebook_with_chunks(
            db_conn, [shared_vec], notebook_name="nb-a", filename="a.pdf"
        )
        nb_b, _ = _setup_notebook_with_chunks(
            db_conn, [shared_vec], notebook_name="nb-b", filename="b.pdf"
        )

        results_a = search_chunks(db_conn, nb_a, shared_vec, k=10)
        results_b = search_chunks(db_conn, nb_b, shared_vec, k=10)

        assert len(results_a) == 1
        assert len(results_b) == 1
        assert results_a[0].filename == "a.pdf"
        assert results_b[0].filename == "b.pdf"

    def test_empty_notebook(self, db_conn: psycopg.Connection) -> None:
        nb = create_notebook(db_conn, "empty")
        db_conn.commit()
        results = search_chunks(db_conn, nb.id, _unit_vector(0), k=5)
        assert results == []

    def test_response_fields(self, db_conn: psycopg.Connection) -> None:
        """Verify all fields of RetrievedChunk are populated correctly."""
        v0 = _unit_vector(0)
        nb_id, doc_id = _setup_notebook_with_chunks(
            db_conn, [v0], filename="report.pdf"
        )

        results = search_chunks(db_conn, nb_id, v0, k=1)
        assert len(results) == 1
        c = results[0]
        assert isinstance(c, RetrievedChunk)
        assert c.document_id == doc_id
        assert c.filename == "report.pdf"
        assert c.page_number == 1
        assert c.chunk_index == 0
        assert c.text == "chunk-0"
        assert c.score == pytest.approx(1.0, abs=1e-6)
        assert isinstance(c.chunk_id, int)

    def test_tie_break_by_chunk_id(self, db_conn: psycopg.Connection) -> None:
        """When scores are equal, results are ordered by chunk_id ascending."""
        # Two orthogonal vectors both at distance 1.0 from the query
        v1, v2 = _unit_vector(1), _unit_vector(2)
        nb_id, _ = _setup_notebook_with_chunks(db_conn, [v1, v2])

        results = search_chunks(db_conn, nb_id, _unit_vector(0), k=10)
        assert len(results) == 2
        assert results[0].chunk_id < results[1].chunk_id


# ---------------------------------------------------------------------------
# services/retrieval.py  — retrieve_chunks
# ---------------------------------------------------------------------------


class TestRetrieveChunksService:
    def test_successful_retrieval(self, db_conn: psycopg.Connection) -> None:
        v0 = _unit_vector(0)
        nb_id, _ = _setup_notebook_with_chunks(db_conn, [v0, _unit_vector(1)])
        embedder = FakeEmbeddingProvider(DIM, vectors=[[v0]])

        results = retrieval_service.retrieve_chunks(
            db_conn, nb_id, "what is this?", embedder=embedder, k=5
        )
        assert len(results) == 2
        assert results[0].score == pytest.approx(1.0, abs=1e-6)

    def test_embedder_called_with_kind_query(
        self, db_conn: psycopg.Connection
    ) -> None:
        v0 = _unit_vector(0)
        nb_id, _ = _setup_notebook_with_chunks(db_conn, [v0])
        embedder = FakeEmbeddingProvider(DIM, vectors=[[v0]])

        retrieval_service.retrieve_chunks(
            db_conn, nb_id, "test?", embedder=embedder
        )
        assert embedder.kinds == ["query"]

    def test_notebook_not_found(self, db_conn: psycopg.Connection) -> None:
        embedder = FakeEmbeddingProvider(DIM)
        with pytest.raises(NotebookNotFoundError):
            retrieval_service.retrieve_chunks(
                db_conn, 999999, "anything", embedder=embedder
            )


# ---------------------------------------------------------------------------
# api/retrieve.py  — POST /notebooks/{id}/retrieve
# ---------------------------------------------------------------------------


def _create_notebook_via_api(client: TestClient, name: str = "Test NB") -> int:
    resp = client.post("/notebooks", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


class TestRetrieveAPI:
    """Integration tests for the retrieve endpoint."""

    @pytest.fixture(autouse=True)
    def _setup_client(self, test_client: TestClient) -> None:
        self.client = test_client

    def _override_embedder(self, embedder: FakeEmbeddingProvider) -> None:
        app.dependency_overrides[get_embedder] = lambda: embedder

    def _teardown_overrides(self) -> None:
        app.dependency_overrides.pop(get_embedder, None)

    # -- happy path --

    def test_retrieve_returns_ordered_chunks(
        self, db_conn: psycopg.Connection
    ) -> None:
        """Full round-trip: insert vectors, query, get ordered results."""
        v0 = _unit_vector(0)
        v1 = _unit_vector(1)
        nb_id, doc_id = _setup_notebook_with_chunks(db_conn, [v0, v1])

        # Embedder returns v0 as the query vector
        self._override_embedder(FakeEmbeddingProvider(DIM, vectors=[[v0]]))
        try:
            resp = self.client.post(
                f"/notebooks/{nb_id}/retrieve",
                json={"question": "hello", "k": 10},
            )
        finally:
            self._teardown_overrides()

        assert resp.status_code == 200
        body = resp.json()
        assert body["question"] == "hello"
        assert body["k"] == 10
        chunks = body["chunks"]
        assert len(chunks) == 2
        assert chunks[0]["score"] == pytest.approx(1.0, abs=1e-6)
        assert chunks[1]["score"] == pytest.approx(0.0, abs=1e-6)

    def test_response_fields(self, db_conn: psycopg.Connection) -> None:
        """Verify every field in the chunk response."""
        v0 = _unit_vector(0)
        nb_id, doc_id = _setup_notebook_with_chunks(
            db_conn, [v0], filename="report.pdf"
        )
        self._override_embedder(FakeEmbeddingProvider(DIM, vectors=[[v0]]))
        try:
            resp = self.client.post(
                f"/notebooks/{nb_id}/retrieve",
                json={"question": "test"},
            )
        finally:
            self._teardown_overrides()

        assert resp.status_code == 200
        chunk = resp.json()["chunks"][0]
        assert chunk["document_id"] == doc_id
        assert chunk["filename"] == "report.pdf"
        assert chunk["page_number"] == 1
        assert chunk["chunk_index"] == 0
        assert chunk["text"] == "chunk-0"
        assert isinstance(chunk["chunk_id"], int)
        assert chunk["score"] == pytest.approx(1.0, abs=1e-6)

    def test_empty_notebook_returns_200(
        self, db_conn: psycopg.Connection
    ) -> None:
        nb = create_notebook(db_conn, "empty")
        db_conn.commit()
        self._override_embedder(FakeEmbeddingProvider(DIM))
        try:
            resp = self.client.post(
                f"/notebooks/{nb.id}/retrieve",
                json={"question": "anything"},
            )
        finally:
            self._teardown_overrides()

        assert resp.status_code == 200
        assert resp.json()["chunks"] == []

    def test_k_greater_than_available(
        self, db_conn: psycopg.Connection
    ) -> None:
        v0 = _unit_vector(0)
        nb_id, _ = _setup_notebook_with_chunks(db_conn, [v0])
        self._override_embedder(FakeEmbeddingProvider(DIM, vectors=[[v0]]))
        try:
            resp = self.client.post(
                f"/notebooks/{nb_id}/retrieve",
                json={"question": "hello", "k": 20},
            )
        finally:
            self._teardown_overrides()

        assert resp.status_code == 200
        assert len(resp.json()["chunks"]) == 1

    # -- error cases --

    def test_unknown_notebook_404(self) -> None:
        self._override_embedder(FakeEmbeddingProvider(DIM))
        try:
            resp = self.client.post(
                "/notebooks/999999/retrieve",
                json={"question": "hello"},
            )
        finally:
            self._teardown_overrides()
        assert resp.status_code == 404

    def test_empty_question_422(self) -> None:
        resp = self.client.post(
            "/notebooks/1/retrieve",
            json={"question": ""},
        )
        assert resp.status_code == 422

    def test_whitespace_question_422(self) -> None:
        resp = self.client.post(
            "/notebooks/1/retrieve",
            json={"question": "   "},
        )
        assert resp.status_code == 422

    def test_k_zero_422(self) -> None:
        resp = self.client.post(
            "/notebooks/1/retrieve",
            json={"question": "hi", "k": 0},
        )
        assert resp.status_code == 422

    def test_k_21_422(self) -> None:
        resp = self.client.post(
            "/notebooks/1/retrieve",
            json={"question": "hi", "k": 21},
        )
        assert resp.status_code == 422

    def test_embed_failure_502(self, db_conn: psycopg.Connection) -> None:
        nb = create_notebook(db_conn, "embed-fail")
        db_conn.commit()

        class FailingEmbedder:
            def embed(
                self,
                texts: list[str],
                *,
                kind: Literal["document", "query"],
            ) -> EmbedResult:
                raise LLMError("boom")

        app.dependency_overrides[get_embedder] = lambda: FailingEmbedder()
        try:
            resp = self.client.post(
                f"/notebooks/{nb.id}/retrieve",
                json={"question": "hello"},
            )
        finally:
            self._teardown_overrides()

        assert resp.status_code == 502

    def test_notebook_isolation_via_api(
        self, db_conn: psycopg.Connection
    ) -> None:
        """Chunks from another notebook never leak through the API."""
        v0 = _unit_vector(0)
        nb_a, _ = _setup_notebook_with_chunks(
            db_conn, [v0], notebook_name="iso-a", filename="a.pdf"
        )
        nb_b, _ = _setup_notebook_with_chunks(
            db_conn, [v0], notebook_name="iso-b", filename="b.pdf"
        )
        self._override_embedder(FakeEmbeddingProvider(DIM, vectors=[[v0]]))
        try:
            resp = self.client.post(
                f"/notebooks/{nb_a}/retrieve",
                json={"question": "test"},
            )
        finally:
            self._teardown_overrides()

        assert resp.status_code == 200
        chunks = resp.json()["chunks"]
        assert len(chunks) == 1
        assert chunks[0]["filename"] == "a.pdf"
