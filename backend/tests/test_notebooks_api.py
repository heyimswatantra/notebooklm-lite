from fastapi.testclient import TestClient
import psycopg
import pytest

from backend.db.connection import get_db


def test_create_and_list_notebooks(test_client: TestClient):
    """POST /notebooks creates a notebook, GET /notebooks lists it."""
    # Create first notebook
    res1 = test_client.post("/notebooks", json={"name": "Alpha"})
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["id"] is not None
    assert data1["name"] == "Alpha"
    assert "created_at" in data1

    # Create second notebook
    res2 = test_client.post("/notebooks", json={"name": "Beta"})
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["id"] is not None
    assert data2["name"] == "Beta"

    # List notebooks
    list_res = test_client.get("/notebooks")
    assert list_res.status_code == 200
    notebooks = list_res.json()
    assert len(notebooks) == 2
    # Ordered by created_at DESC, id DESC -> Beta is first
    assert notebooks[0]["id"] == data2["id"]
    assert notebooks[0]["name"] == "Beta"
    assert notebooks[1]["id"] == data1["id"]
    assert notebooks[1]["name"] == "Alpha"


def test_created_notebook_readable_from_separate_connection(
    test_client: TestClient, test_db_url: str
):
    """get_db() commits on success so created records are visible on a new, separate connection."""
    res = test_client.post("/notebooks", json={"name": "Persisted Notebook"})
    assert res.status_code == 201
    nb_id = res.json()["id"]

    # Open a completely separate connection
    with psycopg.connect(test_db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM notebooks WHERE id = %s;", (nb_id,))
            row = cur.fetchone()
            assert row is not None
            assert row[0] == nb_id
            assert row[1] == "Persisted Notebook"


def test_get_db_rollback_on_error(test_db_url: str):
    """get_db() rolls back the transaction when an exception is raised."""
    # Use get_db directly to simulate a failure midway
    gen = get_db(test_db_url)
    conn = next(gen)

    with conn.cursor() as cur:
        cur.execute("INSERT INTO notebooks (name) VALUES ('Should Rollback');")

    # Raise exception in generator
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("Simulated failure"))

    # Verify on a separate connection that the row was NOT committed
    with psycopg.connect(test_db_url) as check_conn:
        with check_conn.cursor() as cur:
            cur.execute("SELECT * FROM notebooks WHERE name = 'Should Rollback';")
            assert cur.fetchone() is None


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "\t  \n"},
        {"name": "x" * 201},
        {},
    ],
)
def test_create_notebook_validation_422(
    test_client: TestClient, invalid_payload: dict
):
    """Validation: stripped non-empty name up to 200 chars returns 422 Unprocessable Entity."""
    res = test_client.post("/notebooks", json=invalid_payload)
    assert res.status_code == 422


def test_create_notebook_strips_whitespace(test_client: TestClient):
    """Validation: whitespace surrounding the name is stripped."""
    res = test_client.post("/notebooks", json={"name": "   Whitespace Trimmed   "})
    assert res.status_code == 201
    assert res.json()["name"] == "Whitespace Trimmed"
