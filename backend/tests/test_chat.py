"""Tests for M5b: answering service, chat API, and query_logs."""

from __future__ import annotations

import json
from typing import Literal

import psycopg
import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_chat_provider, get_embedder
from backend.llm.base import ChatMessage, ChatResult, LLMError
from backend.main import app
from backend.rag.prompting import NOT_FOUND_MESSAGE, build_messages
from backend.services import answering as answering_service
from backend.services import retrieval as retrieval_service
from tests.fakes import FakeChatProvider, FakeEmbeddingProvider
from tests.helpers import setup_notebook_with_chunks, unit_vector


def _fetch_query_log_count(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM query_logs;")
        row = cur.fetchone()
    assert row is not None
    return row[0]


def _fetch_latest_query_log(conn: psycopg.Connection) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT notebook_id, question, retrieved_chunk_ids, scores,
                   answer, citations, model, prompt_tokens, completion_tokens,
                   latency_ms
              FROM query_logs
             ORDER BY id DESC
             LIMIT 1;
            """
        )
        row = cur.fetchone()
    assert row is not None
    return {
        "notebook_id": row[0],
        "question": row[1],
        "retrieved_chunk_ids": list(row[2]),
        "scores": list(row[3]),
        "answer": row[4],
        "citations": row[5],
        "model": row[6],
        "prompt_tokens": row[7],
        "completion_tokens": row[8],
        "latency_ms": row[9],
    }


class TestChatAPI:
    @pytest.fixture(autouse=True)
    def _setup_client(self, test_client: TestClient) -> None:
        self.client = test_client

    def _override_providers(
        self,
        embedder: FakeEmbeddingProvider,
        chat: FakeChatProvider,
    ) -> None:
        app.dependency_overrides[get_embedder] = lambda: embedder
        app.dependency_overrides[get_chat_provider] = lambda: chat

    def _clear_overrides(self) -> None:
        app.dependency_overrides.pop(get_embedder, None)
        app.dependency_overrides.pop(get_chat_provider, None)

    def test_citations_and_sources(
        self, db_conn: psycopg.Connection
    ) -> None:
        v0, v1 = unit_vector(0), unit_vector(1)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0, v1])
        chat = FakeChatProvider(responses=["Answer from [1] and [2][1]."])
        self._override_providers(FakeEmbeddingProvider(vectors=[[v0]]), chat)
        try:
            resp = self.client.post(
                f"/notebooks/{nb_id}/chat",
                json={"question": "What?", "k": 5},
            )
        finally:
            self._clear_overrides()

        assert resp.status_code == 200
        body = resp.json()
        assert body["answered"] is True
        assert body["citations"] == [1, 2]
        assert len(body["sources"]) == 2
        assert body["sources"][0]["label"] == 1
        assert body["sources"][0]["cited"] is True
        assert body["sources"][1]["cited"] is True

        log = _fetch_latest_query_log(db_conn)
        cited = log["citations"]["cited"]
        chunk_ids = log["retrieved_chunk_ids"]
        assert cited[0]["label"] == 1
        assert cited[0]["chunk_id"] == chunk_ids[0]
        assert cited[1]["label"] == 2
        assert cited[1]["chunk_id"] == chunk_ids[1]

    def test_bracket_formats(self, db_conn: psycopg.Connection) -> None:
        v0, v1, v2 = unit_vector(0), unit_vector(1), unit_vector(2)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0, v1, v2])
        for answer in ("See [1][3].", "See [1, 3]."):
            chat = FakeChatProvider(responses=[answer])
            self._override_providers(FakeEmbeddingProvider(vectors=[[v0]]), chat)
            try:
                resp = self.client.post(
                    f"/notebooks/{nb_id}/chat",
                    json={"question": "q"},
                )
            finally:
                self._clear_overrides()
            assert resp.json()["citations"] == [1, 3]

    def test_invalid_label_in_answer_and_log(
        self, db_conn: psycopg.Connection
    ) -> None:
        v0 = unit_vector(0)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0])
        raw = "Claim [1][9] here."
        chat = FakeChatProvider(responses=[raw])
        self._override_providers(FakeEmbeddingProvider(vectors=[[v0]]), chat)
        try:
            resp = self.client.post(
                f"/notebooks/{nb_id}/chat",
                json={"question": "q"},
            )
        finally:
            self._clear_overrides()

        body = resp.json()
        assert body["answer"] == raw
        assert body["citations"] == [1]
        log = _fetch_latest_query_log(db_conn)
        assert log["citations"]["invalid_labels"] == [9]

    def test_exact_not_found_whitespace(
        self, db_conn: psycopg.Connection
    ) -> None:
        v0 = unit_vector(0)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0])
        chat = FakeChatProvider(responses=[f"  {NOT_FOUND_MESSAGE}  \n"])
        self._override_providers(FakeEmbeddingProvider(vectors=[[v0]]), chat)
        try:
            resp = self.client.post(
                f"/notebooks/{nb_id}/chat",
                json={"question": "q"},
            )
        finally:
            self._clear_overrides()

        body = resp.json()
        assert body["answered"] is False
        assert body["citations"] == []

    def test_uncited_answer_warning(
        self, db_conn: psycopg.Connection, caplog: pytest.LogCaptureFixture
    ) -> None:
        v0 = unit_vector(0)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0])
        chat = FakeChatProvider(responses=["Answer with no labels."])
        self._override_providers(FakeEmbeddingProvider(vectors=[[v0]]), chat)
        try:
            with caplog.at_level("WARNING"):
                resp = self.client.post(
                    f"/notebooks/{nb_id}/chat",
                    json={"question": "q"},
                )
        finally:
            self._clear_overrides()

        assert resp.json()["answered"] is True
        assert resp.json()["citations"] == []
        assert any("no valid citations" in r.message for r in caplog.records)

    def test_empty_notebook_no_chat_call(
        self, db_conn: psycopg.Connection
    ) -> None:
        from backend.db.notebooks import create_notebook

        nb = create_notebook(db_conn, "empty")
        db_conn.commit()
        chat = FakeChatProvider()
        self._override_providers(FakeEmbeddingProvider(), chat)
        try:
            resp = self.client.post(
                f"/notebooks/{nb.id}/chat",
                json={"question": "q"},
            )
        finally:
            self._clear_overrides()

        assert resp.status_code == 200
        assert resp.json()["answered"] is False
        assert chat.calls == []
        log = _fetch_latest_query_log(db_conn)
        assert log["model"] == "none"
        assert log["prompt_tokens"] == 0
        assert log["completion_tokens"] == 0

    def test_query_log_fields(
        self, db_conn: psycopg.Connection
    ) -> None:
        v0, v1 = unit_vector(0), unit_vector(1)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0, v1])
        chat = FakeChatProvider(
            responses=[
                ChatResult(
                    text="Done [2].",
                    model="scripted-model",
                    prompt_tokens=42,
                    completion_tokens=7,
                )
            ]
        )
        self._override_providers(FakeEmbeddingProvider(vectors=[[v0]]), chat)
        try:
            resp = self.client.post(
                f"/notebooks/{nb_id}/chat",
                json={"question": "my question"},
            )
        finally:
            self._clear_overrides()

        assert resp.status_code == 200
        log = _fetch_latest_query_log(db_conn)
        assert log["notebook_id"] == nb_id
        assert log["question"] == "my question"
        assert len(log["retrieved_chunk_ids"]) == 2
        assert len(log["scores"]) == 2
        assert log["answer"] == "Done [2]."
        assert log["model"] == "scripted-model"
        assert log["prompt_tokens"] == 42
        assert log["completion_tokens"] == 7
        assert isinstance(log["latency_ms"], int)

    def test_messages_match_build_messages(
        self, db_conn: psycopg.Connection
    ) -> None:
        v0 = unit_vector(0)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0])
        chat = FakeChatProvider(responses=["ok [1]"])
        embedder = FakeEmbeddingProvider(vectors=[[v0]])
        self._override_providers(embedder, chat)
        try:
            chunks = retrieval_service.retrieve_chunks(
                db_conn, nb_id, "hello", embedder=embedder, k=5
            )
            expected = build_messages("hello", chunks).messages
            self.client.post(
                f"/notebooks/{nb_id}/chat",
                json={"question": "hello"},
            )
        finally:
            self._clear_overrides()

        assert len(chat.calls) == 1
        assert chat.calls[0] == expected

    def test_chat_llm_error_502_no_log(
        self, db_conn: psycopg.Connection
    ) -> None:
        v0 = unit_vector(0)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0])

        class FailingChat:
            def chat(
                self,
                messages: list[ChatMessage],
                *,
                temperature: float = 0.0,
            ) -> ChatResult:
                raise LLMError("chat failed")

        self._override_providers(
            FakeEmbeddingProvider(vectors=[[v0]]),
            FailingChat(),  # type: ignore[arg-type]
        )
        try:
            resp = self.client.post(
                f"/notebooks/{nb_id}/chat",
                json={"question": "q"},
            )
        finally:
            self._clear_overrides()

        assert resp.status_code == 502
        assert _fetch_query_log_count(db_conn) == 0

    def test_insert_failure_500_no_answer(
        self, db_conn: psycopg.Connection, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        v0 = unit_vector(0)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0])
        chat = FakeChatProvider(responses=["Hi [1]"])

        def boom(*args, **kwargs):  # noqa: ANN002, ANN003
            raise RuntimeError("db down")

        monkeypatch.setattr(answering_service, "insert_query_log", boom)
        self._override_providers(FakeEmbeddingProvider(vectors=[[v0]]), chat)
        try:
            resp = self.client.post(
                f"/notebooks/{nb_id}/chat",
                json={"question": "q"},
            )
        finally:
            self._clear_overrides()

        assert resp.status_code == 500
        assert "answer" not in resp.json()

    def test_citations_jsonb_round_trip(
        self, db_conn: psycopg.Connection
    ) -> None:
        v0, v1 = unit_vector(0), unit_vector(1)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0, v1])
        chat = FakeChatProvider(responses=["Both [1][2][9]."])
        self._override_providers(FakeEmbeddingProvider(vectors=[[v0]]), chat)
        try:
            self.client.post(
                f"/notebooks/{nb_id}/chat",
                json={"question": "q"},
            )
        finally:
            self._clear_overrides()

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT citations::text FROM query_logs ORDER BY id DESC LIMIT 1;"
            )
            row = cur.fetchone()
        assert row is not None
        payload = json.loads(row[0])
        assert payload["invalid_labels"] == [9]
        assert [c["label"] for c in payload["cited"]] == [1, 2]

    def test_sentinel_plus_extra_text_warning(
        self, db_conn: psycopg.Connection, caplog: pytest.LogCaptureFixture
    ) -> None:
        v0 = unit_vector(0)
        nb_id, _ = setup_notebook_with_chunks(db_conn, [v0])
        text = f"{NOT_FOUND_MESSAGE} Also see [1]."
        chat = FakeChatProvider(responses=[text])
        self._override_providers(FakeEmbeddingProvider(vectors=[[v0]]), chat)
        try:
            with caplog.at_level("WARNING"):
                resp = self.client.post(
                    f"/notebooks/{nb_id}/chat",
                    json={"question": "q"},
                )
        finally:
            self._clear_overrides()

        body = resp.json()
        assert body["answered"] is True
        assert body["citations"] == [1]
        assert any("NOT_FOUND_MESSAGE" in r.message for r in caplog.records)

    def test_unknown_notebook_404(self) -> None:
        self._override_providers(FakeEmbeddingProvider(), FakeChatProvider())
        try:
            resp = self.client.post(
                "/notebooks/999999/chat",
                json={"question": "hello"},
            )
        finally:
            self._clear_overrides()
        assert resp.status_code == 404

    def test_empty_question_422(self) -> None:
        resp = self.client.post(
            "/notebooks/1/chat",
            json={"question": ""},
        )
        assert resp.status_code == 422

    def test_k_out_of_range_422(self) -> None:
        resp = self.client.post(
            "/notebooks/1/chat",
            json={"question": "hi", "k": 0},
        )
        assert resp.status_code == 422
