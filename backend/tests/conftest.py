import os
import sys
from pathlib import Path
import psycopg
import pytest
from fastapi.testclient import TestClient
from pgvector.psycopg import register_vector

from backend.config import Settings, get_settings
from backend.main import app
from backend.db.connection import get_db

# Ensure scripts directory can be imported both on host and inside container
for candidate in [
    Path(__file__).resolve().parent.parent.parent / "scripts",
    Path(__file__).resolve().parent.parent / "scripts",
]:
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from migrate import run_migrations, get_default_migrations_dir  # type: ignore


@pytest.fixture
def fake_settings() -> Settings:
    """Settings with test values — no real API keys."""
    return Settings(
        DATABASE_URL="postgresql://test:test@localhost:5432/test",
        CHAT_PROVIDER="gemini",
        EMBED_PROVIDER="voyage",
        CHAT_MODEL="gemini-3.8-flash",
        EMBED_MODEL="voyage-4-lite",
        EMBED_DIMENSION=1024,
        GEMINI_API_KEY="fake-gemini-key",
        VOYAGE_API_KEY="fake-voyage-key",
    )


def _get_maintenance_url() -> tuple[str, str]:
    """Returns (maintenance_admin_url, test_db_url)."""
    env_override = os.environ.get("TEST_DATABASE_URL")
    if env_override:
        base = env_override.rsplit("/", 1)[0]
        return f"{base}/postgres", f"{base}/notebooklm_test"

    raw_url = get_settings().DATABASE_URL
    base_parts = raw_url.rsplit("/", 1)[0]
    candidate_maint = f"{base_parts}/postgres"
    try:
        with psycopg.connect(candidate_maint, connect_timeout=1) as conn:
            pass
        return candidate_maint, f"{base_parts}/notebooklm_test"
    except Exception:
        localhost_base = "postgresql://postgres:postgres@localhost:5432"
        return f"{localhost_base}/postgres", f"{localhost_base}/notebooklm_test"


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Creates an isolated test database, runs migrations, and tears it down on session completion."""
    maint_url, target_url = _get_maintenance_url()

    # Drop and recreate test database
    with psycopg.connect(maint_url, autocommit=True) as conn:
        conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = 'notebooklm_test' AND pid <> pg_backend_pid();
            """
        )
        conn.execute("DROP DATABASE IF EXISTS notebooklm_test;")
        conn.execute("CREATE DATABASE notebooklm_test;")

    # Run migrations on the test database
    migrations_dir = get_default_migrations_dir()
    with psycopg.connect(target_url) as conn:
        run_migrations(conn, migrations_dir=migrations_dir)

    yield target_url

    # Teardown
    with psycopg.connect(maint_url, autocommit=True) as conn:
        conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = 'notebooklm_test' AND pid <> pg_backend_pid();
            """
        )
        conn.execute("DROP DATABASE IF EXISTS notebooklm_test;")


@pytest.fixture
def db_conn(test_db_url: str):
    """Yields a psycopg connection to the test database with pgvector registered."""
    conn = psycopg.connect(test_db_url)
    register_vector(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def clean_db(test_db_url: str):
    """Truncates application tables between test runs to ensure isolation."""
    yield
    with psycopg.connect(test_db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE notebooks, documents, chunks, query_logs CASCADE;")


@pytest.fixture
def test_client(test_db_url: str, monkeypatch: pytest.MonkeyPatch):
    """Configures the FastAPI app and its startup check to point at the test database."""
    test_settings = Settings(
        DATABASE_URL=test_db_url,
        CHAT_PROVIDER="gemini",
        EMBED_PROVIDER="voyage",
        CHAT_MODEL="gemini-3.8-flash",
        EMBED_MODEL="voyage-4-lite",
        EMBED_DIMENSION=1024,
    )
    monkeypatch.setattr("backend.main.get_settings", lambda: test_settings)
    monkeypatch.setattr("backend.db.connection.get_settings", lambda: test_settings)

    with TestClient(app) as client:
        yield client
