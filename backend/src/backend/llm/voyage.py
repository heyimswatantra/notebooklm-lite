import time
from typing import Literal

import voyageai
from voyageai import error as voyage_error

from backend.llm.base import EmbedResult, LLMError, LLMRateLimitError, LLMAuthError


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
        batch_size = 128
        all_vectors = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
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
