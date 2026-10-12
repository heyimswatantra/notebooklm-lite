from datetime import datetime
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
import psycopg

from backend.db.connection import get_db
from backend.services import notebooks as notebook_service

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


class CreateNotebookRequest(BaseModel):
    name: str = Field(...)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Notebook name cannot be empty")
        if len(stripped) > 200:
            raise ValueError("Notebook name cannot exceed 200 characters")
        return stripped


class NotebookResponse(BaseModel):
    id: int
    name: str
    created_at: datetime


@router.post("", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
def create_notebook(
    request: CreateNotebookRequest,
    conn: psycopg.Connection = Depends(get_db),
) -> NotebookResponse:
    notebook = notebook_service.create_notebook(conn, request.name)
    return NotebookResponse(
        id=notebook.id,
        name=notebook.name,
        created_at=notebook.created_at,
    )


@router.get("", response_model=list[NotebookResponse])
def list_notebooks(
    conn: psycopg.Connection = Depends(get_db),
) -> list[NotebookResponse]:
    notebooks = notebook_service.list_notebooks(conn)
    return [
        NotebookResponse(
            id=nb.id,
            name=nb.name,
            created_at=nb.created_at,
        )
        for nb in notebooks
    ]
