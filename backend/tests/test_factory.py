import pytest
from backend.config import Settings
from backend.llm.factory import get_chat_provider, get_embedding_provider
from backend.llm.gemini import GeminiChatProvider
from backend.llm.voyage import VoyageEmbeddingProvider

def test_get_chat_provider_gemini(fake_settings: Settings):
    provider = get_chat_provider(fake_settings)
    assert isinstance(provider, GeminiChatProvider)

def test_get_embedding_provider_voyage(fake_settings: Settings):
    provider = get_embedding_provider(fake_settings)
    assert isinstance(provider, VoyageEmbeddingProvider)

def test_get_chat_provider_unknown():
    settings = Settings(CHAT_PROVIDER='unknown', GEMINI_API_KEY='x', VOYAGE_API_KEY='x')
    with pytest.raises(ValueError, match='unknown'):
        get_chat_provider(settings)

def test_get_embedding_provider_unknown():
    settings = Settings(EMBED_PROVIDER='unknown', GEMINI_API_KEY='x', VOYAGE_API_KEY='x')
    with pytest.raises(ValueError, match='unknown'):
        get_embedding_provider(settings)
