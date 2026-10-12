from backend.llm.base import (
    ChatMessage, ChatResult, EmbedResult, LLMError,
)
from typing import Literal

class FakeChatProvider:
    """Returns canned responses. Satisfies ChatProvider protocol."""
    def __init__(self, response_text: str = 'Hello from fake LLM', model: str = 'fake-model'):
        self.response_text = response_text
        self.model = model
        self.last_messages: list[ChatMessage] | None = None
        self.last_temperature: float | None = None

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.0) -> ChatResult:
        self.last_messages = messages
        self.last_temperature = temperature
        return ChatResult(
            text=self.response_text,
            model=self.model,
            prompt_tokens=10,
            completion_tokens=5,
        )


class FakeEmbeddingProvider:
    """Returns canned embeddings. Satisfies EmbeddingProvider protocol."""
    def __init__(self, dimension: int = 1024, model: str = 'fake-embed-model'):
        self.dimension = dimension
        self.model = model

    def embed(self, texts: list[str], *, kind: Literal['document', 'query']) -> EmbedResult:
        # Return a vector of zeros for each text
        vectors = [[0.0] * self.dimension for _ in texts]
        return EmbedResult(
            vectors=vectors,
            model=self.model,
            dimension=self.dimension,
        )
