import time
from typing import Literal

import voyageai
from voyageai import error as voyage_error

from backend.llm.base import EmbedResult, LLMError, LLMRateLimitError, LLMAuthError

# Voyage embed API limits (see chunking.py — use Voyage count_tokens, not tiktoken).
_MAX_BATCH_ITEMS = 128
_MAX_BATCH_TOKENS = 120_000


def _batch_texts_for_embed(
    texts: list[str],
    client: voyageai.Client,
    model: str,
) -> list[list[str]]:
    """Split texts into API batches by item count and total Voyage tokens."""
    if not texts:
        return []

    batches: list[list[str]] = []
    current: list[str] = []

    for text in texts:
        candidate = current + [text]
        if current and (
            len(candidate) > _MAX_BATCH_ITEMS
            or client.count_tokens(candidate, model=model) > _MAX_BATCH_TOKENS
        ):
            batches.append(current)
            current = [text]
        else:
            current = candidate

    if current:
        batches.append(current)
    return batches


class VoyageEmbeddingProvider:
    """Embedding provider using the Voyage AI SDK."""

    def __init__(self, api_key: str, model: str, dimension: int) -> None:
        # Disable Voyage's built-in retries — we handle our own backoff.
        self.client = voyageai.Client(api_key=api_key, max_retries=0)
        self.model = model
        self.dimension = dimension

    def embed(self, texts: list[str], *, kind: Literal["document", "query"]) -> EmbedResult:
        if not texts:
            return EmbedResult(vectors=[], model=self.model, dimension=self.dimension)
            
        input_type = kind
        all_vectors = []

        for batch in _batch_texts_for_embed(texts, self.client, self.model):
            batch_retries = 0
            max_retries = 3
            
            while True:
                try:
                    response = self.client.embed(
                        texts=batch,
                        model=self.model,
                        input_type=input_type
                    )
                    break
                except voyage_error.RateLimitError as e:
                    if batch_retries < max_retries:
                        time.sleep(2 ** batch_retries)
                        batch_retries += 1
                        continue
                    raise LLMRateLimitError(f"Rate limit error: {e}") from e
                except voyage_error.AuthenticationError as e:
                    raise LLMAuthError(f"Authentication error: {e}") from e
                except voyage_error.InvalidRequestError as e:
                    raise LLMError(f"Invalid request error: {e}") from e
                except (voyage_error.ServerError, voyage_error.ServiceUnavailableError, 
                        voyage_error.APIConnectionError, voyage_error.Timeout) as e:
                    if batch_retries < max_retries:
                        time.sleep(2 ** batch_retries)
                        batch_retries += 1
                        continue
                    raise LLMError(f"Voyage connection/server error: {e}") from e
                except voyage_error.VoyageError as e:
                    raise LLMError(f"Voyage API error: {e}") from e
            
            for emb in response.embeddings:
                if len(emb) != self.dimension:
                    raise LLMError(f"Embedding dimension mismatch. Expected {self.dimension}, got {len(emb)}")
            
            all_vectors.extend(response.embeddings)
            
        return EmbedResult(
            vectors=all_vectors,
            model=self.model,
            dimension=self.dimension
        )
