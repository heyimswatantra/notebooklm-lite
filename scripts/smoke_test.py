#!/usr/bin/env python
"""Smoke test — verifies real API keys and model names.

Run manually:  cd backend && uv run python ../scripts/smoke_test.py
Never run by pytest.
"""
import sys
import os

# Add backend src to path so imports work when run from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

from backend.config import get_settings
from backend.llm.factory import get_chat_provider, get_embedding_provider
from backend.llm.base import ChatMessage

def main() -> None:
    settings = get_settings()
    print(f'Chat provider:  {settings.CHAT_PROVIDER} / {settings.CHAT_MODEL}')
    print(f'Embed provider: {settings.EMBED_PROVIDER} / {settings.EMBED_MODEL}')
    print(f'Embed dimension: {settings.EMBED_DIMENSION}')
    print()
    
    # --- Embedding test ---
    print('=== Embedding test ===')
    embed_provider = get_embedding_provider(settings)
    result = embed_provider.embed(['Hello, world!'], kind='document')
    print(f'Model:     {result.model}')
    print(f'Dimension: {result.dimension}')
    print(f'Vector len: {len(result.vectors[0])}')
    print(f'First 5:   {result.vectors[0][:5]}')
    print()

    # --- Chat test ---
    print('=== Chat test ===')
    chat_provider = get_chat_provider(settings)
    messages = [
        ChatMessage(role='system', content='You are a helpful assistant. Reply in one sentence.'),
        ChatMessage(role='user', content='What is RAG in the context of LLMs?'),
    ]
    result = chat_provider.chat(messages, temperature=0.0)
    print(f'Model:       {result.model}')
    print(f'Response:    {result.text}')
    print(f'Prompt tok:  {result.prompt_tokens}')
    print(f'Compl. tok:  {result.completion_tokens}')
    print()
    print('Smoke test passed.')

if __name__ == '__main__':
    main()
