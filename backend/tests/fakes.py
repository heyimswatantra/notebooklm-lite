from typing import Literal

from backend.llm.base import (
    ChatMessage,
    ChatResult,
    EmbedResult,
    LLMError,
)


class FakeChatProvider:
    """Scripted chat responses. Satisfies ChatProvider protocol."""

    def __init__(
        self,
        responses: list[str | ChatResult] | None = None,
        *,
        default_text: str = "Hello from fake LLM",
        model: str = "fake-model",
    ):
        if responses is None:
            responses = [default_text]
        self._responses: list[str | ChatResult] = list(responses)
        self.default_model = model
        self.calls: list[list[ChatMessage]] = []
        self.temperatures: list[float] = []

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.0) -> ChatResult:
        self.calls.append(list(messages))
        self.temperatures.append(temperature)
        if not self._responses:
            raise LLMError("FakeChatProvider: no scripted responses left")
        item = self._responses.pop(0)
        if isinstance(item, ChatResult):
            return item
        return ChatResult(
            text=item,
            model=self.default_model,
            prompt_tokens=10,
            completion_tokens=5,
        )


class FakeEmbeddingProvider:
    """Returns canned embeddings. Satisfies EmbeddingProvider protocol.

    If *vectors* is supplied the provider pops from that list on each call
    (one entry per ``embed()`` call, each entry is the full list of vectors
    to return).  Otherwise every text gets a zero-vector.

    *kinds* records every ``kind`` value received, so tests can assert
    ``kind="query"`` was used.
    """

    def __init__(
        self,
        dimension: int = 1024,
        model: str = "fake-embed-model",
        vectors: list[list[list[float]]] | None = None,
    ):
        self.dimension = dimension
        self.model = model
        self._vectors = list(vectors) if vectors is not None else None
        self.kinds: list[str] = []

    def embed(self, texts: list[str], *, kind: Literal["document", "query"]) -> EmbedResult:
        self.kinds.append(kind)
        if self._vectors:
            vecs = self._vectors.pop(0)
        else:
            vecs = [[0.0] * self.dimension for _ in texts]
        return EmbedResult(
            vectors=vecs,
            model=self.model,
            dimension=self.dimension,
        )
