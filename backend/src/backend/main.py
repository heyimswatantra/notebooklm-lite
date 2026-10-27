from contextlib import asynccontextmanager
from fastapi import FastAPI

from backend.config import get_settings
from backend.db.connection import get_connection
from backend.db.checks import verify_embedding_dimension
from backend.api.notebooks import router as notebooks_router
from backend.api.documents import router as documents_router
from backend.api.chat import router as chat_router
from backend.api.retrieve import router as retrieve_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    with get_connection() as conn:
        verify_embedding_dimension(conn, settings.EMBED_DIMENSION)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(notebooks_router)
app.include_router(documents_router)
app.include_router(retrieve_router)
app.include_router(chat_router)
