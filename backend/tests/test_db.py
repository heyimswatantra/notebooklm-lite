import psycopg
import pytest

from backend.db.checks import verify_embedding_dimension
from backend.db.documents import insert_chunks, insert_document
from backend.db.notebooks import create_notebook, list_notebooks
from backend.rag.chunking import Chunk
from migrate import run_migrations, get_default_migrations_dir  # type: ignore


def test_migration_runner_is_idempotent(db_conn: psycopg.Connection):
    """Running migrations repeatedly is a safe no-op once applied."""
    migrations_dir = get_default_migrations_dir()
    # First re-run: already applied in fixture, should return empty list
    applied = run_migrations(db_conn, migrations_dir=migrations_dir)
    assert applied == []

    # Second re-run: still empty list, no errors
    applied_again = run_migrations(db_conn, migrations_dir=migrations_dir)
    assert applied_again == []


def test_schema_tables_and_indexes_exist(db_conn: psycopg.Connection):
    """Verifies that all tables, extension, unique constraints, and indexes exist."""
    with db_conn.cursor() as cur:
        # Check pgvector extension
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
        assert cur.fetchone() is not None, "pgvector extension is not installed"

        # Check tables exist
        cur.execute(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public';
            """
        )
        tables = {row[0] for row in cur.fetchall()}
        expected_tables = {
            "schema_migrations",
            "notebooks",
            "documents",
            "chunks",
            "query_logs",
        }
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

        # Check unique constraint on chunks (document_id, chunk_index)
        cur.execute(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'chunks'::regclass
              AND contype = 'u';
            """
        )
        constraints = [row[0] for row in cur.fetchall()]
        assert "uq_chunks_document_chunk_index" in constraints

        # Check btree indexes on documents(notebook_id) and chunks(document_id)
        cur.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename IN ('documents', 'chunks');
            """
        )
        indexes = {row[0] for row in cur.fetchall()}
        assert "idx_documents_notebook_id" in indexes
        assert "idx_chunks_document_id" in indexes


def test_embedding_dimension_check_passes(db_conn: psycopg.Connection):
    """Dimension check succeeds when chunks.embedding matches expected 1024."""
    verify_embedding_dimension(db_conn, expected_dim=1024)


def test_embedding_dimension_check_fails_on_mismatch(db_conn: psycopg.Connection):
    """Dimension check fails with a clear message when format_type() does not match."""
    # Create a scratch table with dimension 768
    with db_conn.cursor() as cur:
        cur.execute(
            """
            CREATE TEMP TABLE scratch_chunks (
                id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                embedding vector(768) NOT NULL
            );
            """
        )

    with pytest.raises(RuntimeError) as exc_info:
        verify_embedding_dimension(
            db_conn, expected_dim=1024, table_name="scratch_chunks"
        )

    error_msg = str(exc_info.value)
    assert "dimension mismatch" in error_msg
    assert "vector(768)" in error_msg
    assert "1024" in error_msg


def test_embedding_dimension_check_fails_on_missing_table(db_conn: psycopg.Connection):
    """Dimension check fails with a clear message if table or column is missing."""
    with pytest.raises(RuntimeError) as exc_info:
        verify_embedding_dimension(
            db_conn, expected_dim=1024, table_name="nonexistent_chunks"
        )

    error_msg = str(exc_info.value)
    assert "does not exist" in error_msg
    assert "run migrations" in error_msg


def test_chunk_insert_accepts_plain_list_float_1024(db_conn: psycopg.Connection):
    """pgvector + psycopg accept list[float] embeddings at dimension 1024."""
    nb = create_notebook(db_conn, "Vector test")
    doc = insert_document(db_conn, nb.id, "sample.pdf", page_count=1)
    vector = [0.01] * 1024
    chunks = [Chunk(chunk_index=0, page_number=1, text="hello", token_count=1)]
    insert_chunks(db_conn, doc.id, chunks, [vector], "test-model")
    db_conn.commit()

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT vector_dims(embedding) FROM chunks WHERE document_id = %s;",
            (doc.id,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == 1024


def test_db_notebook_crud(db_conn: psycopg.Connection):
    """Tests create_notebook and list_notebooks raw SQL functions and ordering."""
    nb1 = create_notebook(db_conn, "First Notebook")
    nb2 = create_notebook(db_conn, "Second Notebook")

    assert nb1.id is not None
    assert nb1.name == "First Notebook"
    assert nb2.id is not None
    assert nb2.name == "Second Notebook"

    notebooks = list_notebooks(db_conn)
    assert len(notebooks) == 2
    # Ordered by created_at DESC, id DESC
    assert notebooks[0].id == nb2.id
    assert notebooks[1].id == nb1.id
