#!/usr/bin/env python
"""Database migration runner.

Applies numbered .sql files from backend/db/migrations/ in order,
records applied files in schema_migrations, and is idempotent (safe to run repeatedly).
"""
import argparse
import os
import sys
from pathlib import Path
import psycopg

# Ensure backend package can be imported if running standalone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backend.config import get_settings


def get_default_migrations_dir() -> Path:
    base = Path(__file__).resolve().parent.parent
    candidate1 = base / "backend" / "db" / "migrations"
    if candidate1.is_dir():
        return candidate1
    candidate2 = base / "db" / "migrations"
    if candidate2.is_dir():
        return candidate2
    raise FileNotFoundError(
        f"Migrations directory not found in {candidate1} or {candidate2}"
    )


def run_migrations(
    conn: psycopg.Connection, migrations_dir: Path | None = None
) -> list[str]:
    """Applies pending SQL migrations in alphabetical order.

    Each migration runs in its own transaction along with its schema_migrations entry.
    Returns the list of applied migration filenames.
    """
    if migrations_dir is None:
        migrations_dir = get_default_migrations_dir()

    # Ensure schema_migrations table exists
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename text PRIMARY KEY,
                    applied_at timestamptz NOT NULL DEFAULT now()
                );
                """
            )

    # Get already applied migrations
    with conn.cursor() as cur:
        cur.execute("SELECT filename FROM schema_migrations;")
        applied = {row[0] for row in cur.fetchall()}

    # Discover and sort migration files
    sql_files = sorted(migrations_dir.glob("*.sql"), key=lambda p: p.name)
    newly_applied: list[str] = []

    for sql_file in sql_files:
        if sql_file.name in applied:
            continue

        sql_content = sql_file.read_text(encoding="utf-8")
        # One transaction per migration file, including the schema_migrations insert
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(sql_content)
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s);",
                    (sql_file.name,),
                )
        print(f"Applied migration: {sql_file.name}")
        newly_applied.append(sql_file.name)

    if not newly_applied:
        print("Database is up to date. No pending migrations.")

    return newly_applied


def main() -> None:
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL (defaults to Settings.DATABASE_URL)",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=None,
        help="Directory containing .sql migrations",
    )
    args = parser.parse_args()

    db_url = args.db_url or get_settings().DATABASE_URL
    migrations_dir = args.migrations_dir or get_default_migrations_dir()

    # Plain psycopg.connect with no register_vector
    with psycopg.connect(db_url) as conn:
        run_migrations(conn, migrations_dir=migrations_dir)


if __name__ == "__main__":
    main()
