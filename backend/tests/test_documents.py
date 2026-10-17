"""Tests for document upload, ingestion service, and list endpoints."""
from __future__ import annotations

from typing import Literal

import pymupdf
import psycopg
import pytest
from fastapi.testclient import TestClient

from backend.api.documents import get_embedder
from backend.db.notebooks import create_notebook
from backend.llm.base import EmbedResult, LLMError
from backend.main import app
from backend.services import ingestion as ingestion_service
from backend.services.ingestion import NotebookNotFoundError
from tests.fakes import FakeEmbeddingProvider


def _make_pdf(pages_text: list[str]) -> bytes:
    doc = pymupdf.Document()
    for text in pages_text:
        page = doc.new_page(width=612, height=792)
        if text:
            page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _create_notebook(client: TestClient, name: str = "Test NB") -> int:
    resp = client.post("/notebooks", json={"name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
def doc_client(test_client: TestClient):
    app.dependency_overrides[get_embedder] = lambda: FakeEmbeddingProvider(1024)
    yield test_client
    app.dependency_overrides.pop(get_embedder, None)


class FailingEmbeddingProvider:
    def __init__(self) -> None:
        self.model = "fail-model"
        self.dimension = 1024

    def embed(self, texts: list[str], *, kind: Literal["document", "query"]) -> EmbedResult:
        raise LLMError("embed failed")


class TestIngestDocumentService:
    def test_successful_ingest(self, db_conn: psycopg.Connection) -> None:
        nb = create_notebook(db_conn, "ingest")
        pdf = _make_pdf(["Page one text.", "Page two text."])
        embedder = FakeEmbeddingProvider(1024)

        summary = ingestion_service.ingest_document(
            db_conn,
            nb.id,
            "report.pdf",
            pdf,
            embedder=embedder,
        )
        db_conn.commit()

        assert summary.filename == "report.pdf"
        assert summary.page_count == 2
        assert summary.chunk_count >= 1

        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documents WHERE notebook_id = %s;", (nb.id,))
            assert cur.fetchone()[0] == 1

            cur.execute(
                """
                SELECT chunk_index, page_number, embedding_model, vector_dims(embedding)
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.notebook_id = %s
                ORDER BY chunk_index;
                """,
                (nb.id,),
            )
            rows = cur.fetchall()
            assert len(rows) == summary.chunk_count
            indices = [r[0] for r in rows]
            assert indices == list(range(len(rows)))
            assert all(r[1] in (1, 2) for r in rows)
            assert all(r[2] == "fake-embed-model" for r in rows)
            assert all(r[3] == 1024 for r in rows)

    def test_failed_embed_leaves_zero_rows(self, db_conn: psycopg.Connection) -> None:
        nb = create_notebook(db_conn, "no-embed")
        pdf = _make_pdf(["Some text"])

        with pytest.raises(LLMError):
            ingestion_service.ingest_document(
                db_conn,
                nb.id,
                "doc.pdf",
                pdf,
                embedder=FailingEmbeddingProvider(),
            )
        db_conn.rollback()

        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documents;")
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM chunks;")
            assert cur.fetchone()[0] == 0


class TestDocumentsAPI:
    def test_unknown_notebook_post_404(self, doc_client: TestClient) -> None:
        pdf = _make_pdf(["hello"])
        resp = doc_client.post(
            "/notebooks/999999/documents",
            files={"file": ("x.pdf", pdf, "application/pdf")},
        )
        assert resp.status_code == 404

    def test_unknown_notebook_get_404(self, doc_client: TestClient) -> None:
        resp = doc_client.get("/notebooks/999999/documents")
        assert resp.status_code == 404

    def test_non_pdf_extension_400(self, doc_client: TestClient) -> None:
        nb_id = _create_notebook(doc_client)
        resp = doc_client.post(
            f"/notebooks/{nb_id}/documents",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400
        assert "PDF" in resp.json()["detail"]

    def test_non_pdf_content_400(self, doc_client: TestClient) -> None:
        nb_id = _create_notebook(doc_client)
        resp = doc_client.post(
            f"/notebooks/{nb_id}/documents",
            files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
        )
        assert resp.status_code == 400

    def test_corrupt_pdf_with_header_400(self, doc_client: TestClient) -> None:
        nb_id = _create_notebook(doc_client)
        corrupt = b"%PDF-1.4\nnot a valid pdf body"
        resp = doc_client.post(
            f"/notebooks/{nb_id}/documents",
            files={"file": ("bad.pdf", corrupt, "application/pdf")},
        )
        assert resp.status_code == 400

    def test_file_too_large_413(self, doc_client: TestClient) -> None:
        nb_id = _create_notebook(doc_client)
        huge = b"%PDF-" + b"x" * (20 * 1024 * 1024)
        resp = doc_client.post(
            f"/notebooks/{nb_id}/documents",
            files={"file": ("big.pdf", huge, "application/pdf")},
        )
        assert resp.status_code == 413

    def test_no_text_pdf_422(self, doc_client: TestClient) -> None:
        nb_id = _create_notebook(doc_client)
        blank_pdf = _make_pdf(["", ""])
        resp = doc_client.post(
            f"/notebooks/{nb_id}/documents",
            files={"file": ("blank.pdf", blank_pdf, "application/pdf")},
        )
        assert resp.status_code == 422

    def test_embed_error_502(self, doc_client: TestClient) -> None:
        nb_id = _create_notebook(doc_client)
        app.dependency_overrides[get_embedder] = lambda: FailingEmbeddingProvider()
        pdf = _make_pdf(["content"])
        resp = doc_client.post(
            f"/notebooks/{nb_id}/documents",
            files={"file": ("doc.pdf", pdf, "application/pdf")},
        )
        assert resp.status_code == 502

    def test_chunk_insert_failure_rolls_back(
        self, doc_client: TestClient, db_conn: psycopg.Connection
    ) -> None:
        """Wrong-dimension vectors fail insert; API returns 500; no document rows remain."""
        nb_id = _create_notebook(doc_client)
        app.dependency_overrides[get_embedder] = lambda: FakeEmbeddingProvider(768)
        pdf = _make_pdf(["rollback test"])
        resp = doc_client.post(
            f"/notebooks/{nb_id}/documents",
            files={"file": ("doc.pdf", pdf, "application/pdf")},
        )
        assert resp.status_code == 500
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documents;")
            assert cur.fetchone()[0] == 0

    def test_get_documents_with_chunk_count(self, doc_client: TestClient) -> None:
        nb_id = _create_notebook(doc_client)
        pdf = _make_pdf(["One page of content for listing."])
        post = doc_client.post(
            f"/notebooks/{nb_id}/documents",
            files={"file": ("listed.pdf", pdf, "application/pdf")},
        )
        assert post.status_code == 201
        created = post.json()

        listing = doc_client.get(f"/notebooks/{nb_id}/documents")
        assert listing.status_code == 200
        docs = listing.json()
        assert len(docs) == 1
        assert docs[0]["id"] == created["id"]
        assert docs[0]["filename"] == "listed.pdf"
        assert docs[0]["chunk_count"] == created["chunk_count"]

    def test_documents_isolated_by_notebook(self, doc_client: TestClient) -> None:
        nb_a = _create_notebook(doc_client, "A")
        nb_b = _create_notebook(doc_client, "B")
        pdf = _make_pdf(["shared content"])

        doc_client.post(
            f"/notebooks/{nb_a}/documents",
            files={"file": ("a.pdf", pdf, "application/pdf")},
        )
        doc_client.post(
            f"/notebooks/{nb_b}/documents",
            files={"file": ("b.pdf", pdf, "application/pdf")},
        )

        list_a = doc_client.get(f"/notebooks/{nb_a}/documents").json()
        list_b = doc_client.get(f"/notebooks/{nb_b}/documents").json()
        assert len(list_a) == 1
        assert len(list_b) == 1
        assert list_a[0]["filename"] == "a.pdf"
        assert list_b[0]["filename"] == "b.pdf"

    def test_filename_stored_as_basename(self, doc_client: TestClient) -> None:
        nb_id = _create_notebook(doc_client)
        pdf = _make_pdf(["basename test"])
        resp = doc_client.post(
            f"/notebooks/{nb_id}/documents",
            files={"file": ("/tmp/evil/path/myfile.pdf", pdf, "application/pdf")},
        )
        assert resp.status_code == 201
        assert resp.json()["filename"] == "myfile.pdf"
