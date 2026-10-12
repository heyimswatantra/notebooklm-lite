from backend.config import Settings
from backend.llm.base import ChatProvider, EmbeddingProvider

def get_chat_provider(settings: Settings) -> ChatProvider:
    if settings.CHAT_PROVIDER == "gemini":
        from backend.llm.gemini import GeminiChatProvider
        return GeminiChatProvider(api_key=settings.GEMINI_API_KEY, model=settings.CHAT_MODEL)
    else:
        raise ValueError(f"Unsupported CHAT_PROVIDER: {settings.CHAT_PROVIDER}")

def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.EMBED_PROVIDER == "voyage":
        from backend.llm.voyage import VoyageEmbeddingProvider
        return VoyageEmbeddingProvider(
            api_key=settings.VOYAGE_API_KEY,
            model=settings.EMBED_MODEL,
            dimension=settings.EMBED_DIMENSION
        )
    else:
        raise ValueError(f"Unsupported EMBED_PROVIDER: {settings.EMBED_PROVIDER}")
