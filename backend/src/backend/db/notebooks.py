from dataclasses import dataclass
from datetime import datetime
import psycopg


@dataclass(frozen=True)
class Notebook:
    id: int
    name: str
    created_at: datetime


def create_notebook(conn: psycopg.Connection, name: str) -> Notebook:
    """Inserts a new notebook and returns the created record."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO notebooks (name)
            VALUES (%s)
            RETURNING id, name, created_at;
            """,
            (name,),
        )
        row = cur.fetchone()
        assert row is not None
        return Notebook(id=row[0], name=row[1], created_at=row[2])


def list_notebooks(conn: psycopg.Connection) -> list[Notebook]:
    """Returns all notebooks ordered by created_at DESC, id DESC."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, created_at
            FROM notebooks
            ORDER BY created_at DESC, id DESC;
            """
        )
        rows = cur.fetchall()
        return [Notebook(id=r[0], name=r[1], created_at=r[2]) for r in rows]
