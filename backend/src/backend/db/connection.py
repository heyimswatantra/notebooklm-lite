from collections.abc import Generator
import psycopg
from pgvector.psycopg import register_vector
from backend.config import get_settings


def get_connection(db_url: str | None = None) -> psycopg.Connection:
    """Creates a psycopg connection and registers pgvector types."""
    url = db_url or get_settings().DATABASE_URL
    conn = psycopg.connect(url)
    register_vector(conn)
    return conn


def get_db(db_url: str | None = None) -> Generator[psycopg.Connection, None, None]:
    """FastAPI dependency yielding a connection.

    Commits on success and rolls back on error.
    """
    conn = get_connection(db_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
