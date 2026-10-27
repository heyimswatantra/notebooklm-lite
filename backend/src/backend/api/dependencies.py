"""Shared FastAPI dependencies for the API layer.

get_db  — yields a psycopg connection (commit on success, rollback on error).
get_embedder — returns the configured EmbeddingProvider.
get_chat_provider — returns the configured ChatProvider.

These are the sole touchpoints between api/ and llm/factory + db/connection.
"""

from backend.config import get_settings
from backend.db.connection import get_db  # noqa: F401 — re-exported for Depends()
from backend.llm.base import ChatProvider, EmbeddingProvider
from backend.llm.factory import get_chat_provider as _get_chat_provider
from backend.llm.factory import get_embedding_provider


def get_embedder() -> EmbeddingProvider:
    """FastAPI dependency — configured embedding provider."""
    return get_embedding_provider(get_settings())


def get_chat_provider() -> ChatProvider:
    """FastAPI dependency — configured chat provider."""
    return _get_chat_provider(get_settings())
