import psycopg


def verify_embedding_dimension(
    conn: psycopg.Connection,
    expected_dim: int,
    table_name: str = "chunks",
    column_name: str = "embedding",
) -> None:
    """Verifies that the embedding column exists and has vector(expected_dim) type via format_type()."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            WHERE a.attrelid = to_regclass(%s)
              AND a.attname = %s;
            """,
            (table_name, column_name),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(
                f"Startup check failed: table '{table_name}' or column '{column_name}' does not exist. "
                "Please run migrations before starting the application."
            )
        actual_type = row[0]
        expected_type = f"vector({expected_dim})"
        if actual_type != expected_type:
            raise RuntimeError(
                f"Startup check failed: {table_name}.{column_name} dimension mismatch! "
                f"Database column has type '{actual_type}', but EMBED_DIMENSION is configured as {expected_dim} ({expected_type})."
            )
