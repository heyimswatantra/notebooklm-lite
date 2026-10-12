import psycopg
from backend.db import notebooks as db_notebooks
from backend.db.notebooks import Notebook


def create_notebook(conn: psycopg.Connection, name: str) -> Notebook:
    """Orchestrates notebook creation."""
    return db_notebooks.create_notebook(conn, name)


def list_notebooks(conn: psycopg.Connection) -> list[Notebook]:
    """Orchestrates notebook listing."""
    return db_notebooks.list_notebooks(conn)
