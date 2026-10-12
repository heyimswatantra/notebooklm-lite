import pytest
from backend.config import Settings

@pytest.fixture
def fake_settings() -> Settings:
    """Settings with test values — no real API keys."""
    return Settings(
        DATABASE_URL='postgresql://test:test@localhost:5432/test',
        CHAT_PROVIDER='gemini',
        EMBED_PROVIDER='voyage',
        CHAT_MODEL='gemini-3.8-flash',
        EMBED_MODEL='voyage-4-lite',
        EMBED_DIMENSION=1024,
        GEMINI_API_KEY='fake-gemini-key',
        VOYAGE_API_KEY='fake-voyage-key',
    )
