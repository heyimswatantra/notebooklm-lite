import os
import pytest
from backend.config import Settings

def test_settings_defaults():
    s = Settings()
    assert s.CHAT_PROVIDER == 'gemini'
    assert s.EMBED_PROVIDER == 'voyage'
    assert s.EMBED_DIMENSION == 1024
    assert s.CHAT_MODEL == 'gemini-3.8-flash'
    assert s.EMBED_MODEL == 'voyage-4-lite'

def test_settings_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('CHAT_MODEL', 'test-model')
    monkeypatch.setenv('EMBED_DIMENSION', '512')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    s = Settings()
    assert s.CHAT_MODEL == 'test-model'
    assert s.EMBED_DIMENSION == 512
    assert s.GEMINI_API_KEY == 'test-key'

def test_settings_is_frozen():
    s = Settings()
    with pytest.raises(Exception):  # ValidationError for frozen model
        s.CHAT_MODEL = 'other'  # type: ignore[misc]
