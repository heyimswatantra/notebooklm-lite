from dataclasses import dataclass
from typing import Literal, Protocol

@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str

@dataclass(frozen=True)
class ChatResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int

@dataclass(frozen=True)
class EmbedResult:
    vectors: list[list[float]]
    model: str
    dimension: int

class LLMError(Exception): ...
class LLMRateLimitError(LLMError): ...
class LLMAuthError(LLMError): ...

class ChatProvider(Protocol):
    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.0) -> ChatResult: ...

class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str], *, kind: Literal["document", "query"]) -> EmbedResult: ...
