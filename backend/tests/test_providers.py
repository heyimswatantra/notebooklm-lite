from unittest.mock import MagicMock, patch
import pytest
from google.genai import errors as genai_errors
from voyageai import error as voyage_errors

from backend.llm.base import ChatMessage, ChatResult, EmbedResult, LLMError, LLMRateLimitError, LLMAuthError
from backend.llm.gemini import GeminiChatProvider
from backend.llm.voyage import VoyageEmbeddingProvider


# ==============================================================================
# GeminiChatProvider Tests
# ==============================================================================

def test_gemini_chat_success():
    provider = GeminiChatProvider(api_key="test-api-key", model="gemini-3.8-flash")
    
    mock_response = MagicMock()
    mock_response.text = "This is a response."
    mock_response.usage_metadata.prompt_token_count = 15
    mock_response.usage_metadata.candidates_token_count = 8
    
    provider.client.models.generate_content = MagicMock(return_value=mock_response)
    
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Hello!"),
        ChatMessage(role="assistant", content="Hi there!"),
        ChatMessage(role="user", content="How are you?"),
    ]
    
    result = provider.chat(messages, temperature=0.5)
    
    assert isinstance(result, ChatResult)
    assert result.text == "This is a response."
    assert result.model == "gemini-3.8-flash"
    assert result.prompt_tokens == 15
    assert result.completion_tokens == 8
    
    provider.client.models.generate_content.assert_called_once()
    call_kwargs = provider.client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-3.8-flash"
    assert call_kwargs["config"].system_instruction == "You are a helpful assistant."
    assert call_kwargs["config"].temperature == 0.5
    assert len(call_kwargs["contents"]) == 3
    # Check role mapping: assistant -> model
    assert call_kwargs["contents"][0].role == "user"
    assert call_kwargs["contents"][1].role == "model"
    assert call_kwargs["contents"][2].role == "user"


@patch("time.sleep", return_value=None)
def test_gemini_chat_rate_limit_retry_and_exhaustion(mock_sleep):
    provider = GeminiChatProvider(api_key="test-api-key", model="gemini-3.8-flash")
    
    # 429 ClientError
    error_429 = genai_errors.ClientError(429, "Rate limit exceeded")
    provider.client.models.generate_content = MagicMock(side_effect=error_429)
    
    with pytest.raises(LLMRateLimitError):
        provider.chat([ChatMessage(role="user", content="Hi")])
    
    # Called 1 initial + 3 retries = 4 times
    assert provider.client.models.generate_content.call_count == 4
    assert mock_sleep.call_count == 3


@patch("time.sleep", return_value=None)
def test_gemini_chat_rate_limit_retry_success(mock_sleep):
    provider = GeminiChatProvider(api_key="test-api-key", model="gemini-3.8-flash")
    
    mock_response = MagicMock()
    mock_response.text = "Success on second try"
    mock_response.usage_metadata.prompt_token_count = 10
    mock_response.usage_metadata.candidates_token_count = 5
    
    error_429 = genai_errors.ClientError(429, "Rate limit exceeded")
    provider.client.models.generate_content = MagicMock(side_effect=[error_429, mock_response])
    
    result = provider.chat([ChatMessage(role="user", content="Hi")])
    assert result.text == "Success on second try"
    assert provider.client.models.generate_content.call_count == 2
    assert mock_sleep.call_count == 1


def test_gemini_chat_auth_error_no_retry():
    provider = GeminiChatProvider(api_key="test-api-key", model="gemini-3.8-flash")
    
    error_401 = genai_errors.ClientError(401, "Invalid API key")
    provider.client.models.generate_content = MagicMock(side_effect=error_401)
    
    with pytest.raises(LLMAuthError):
        provider.chat([ChatMessage(role="user", content="Hi")])
    
    assert provider.client.models.generate_content.call_count == 1


# ==============================================================================
# VoyageEmbeddingProvider Tests
# ==============================================================================

def test_voyage_embed_success():
    provider = VoyageEmbeddingProvider(api_key="test-api-key", model="voyage-4-lite", dimension=4)
    
    mock_response = MagicMock()
    mock_response.embeddings = [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]
    provider.client.embed = MagicMock(return_value=mock_response)
    provider.client.count_tokens = MagicMock(return_value=2)

    result = provider.embed(["doc 1", "doc 2"], kind="document")
    
    assert isinstance(result, EmbedResult)
    assert result.dimension == 4
    assert result.model == "voyage-4-lite"
    assert len(result.vectors) == 2
    assert result.vectors[0] == [0.1, 0.2, 0.3, 0.4]
    provider.client.embed.assert_called_once_with(
        texts=["doc 1", "doc 2"],
        model="voyage-4-lite",
        input_type="document"
    )


def test_voyage_embed_empty():
    provider = VoyageEmbeddingProvider(api_key="test-api-key", model="voyage-4-lite", dimension=4)
    provider.client.embed = MagicMock()
    
    result = provider.embed([], kind="query")
    assert result.vectors == []
    assert result.dimension == 4
    provider.client.embed.assert_not_called()


def test_voyage_embed_dimension_mismatch():
    provider = VoyageEmbeddingProvider(api_key="test-api-key", model="voyage-4-lite", dimension=1024)
    
    # Return vector of length 3 instead of 1024
    mock_response = MagicMock()
    mock_response.embeddings = [[0.1, 0.2, 0.3]]
    provider.client.embed = MagicMock(return_value=mock_response)
    provider.client.count_tokens = MagicMock(return_value=1)

    with pytest.raises(LLMError, match="dimension mismatch"):
        provider.embed(["test"], kind="document")


def test_voyage_embed_batching():
    provider = VoyageEmbeddingProvider(api_key="test-api-key", model="voyage-4-lite", dimension=2)

    # 200 texts -> should produce 2 batches (128 + 72)
    texts = [f"text {i}" for i in range(200)]

    def mock_embed(texts, model, input_type):
        res = MagicMock()
        res.embeddings = [[0.1, 0.2] for _ in texts]
        return res

    provider.client.embed = MagicMock(side_effect=mock_embed)
    provider.client.count_tokens = MagicMock(side_effect=lambda t, model: len(t))

    result = provider.embed(texts, kind="document")
    assert len(result.vectors) == 200
    assert provider.client.embed.call_count == 2


def test_voyage_embed_batches_by_token_limit():
    provider = VoyageEmbeddingProvider(api_key="test-api-key", model="voyage-4-lite", dimension=2)

    texts = ["a", "b", "c", "d"]

    def mock_embed(texts, model, input_type):
        res = MagicMock()
        res.embeddings = [[0.1, 0.2] for _ in texts]
        return res

    provider.client.embed = MagicMock(side_effect=mock_embed)

    # Force a new batch after two items based on token total (not item count).
    def mock_count_tokens(batch, model):
        return len(batch) * 60_000

    provider.client.count_tokens = MagicMock(side_effect=mock_count_tokens)

    result = provider.embed(texts, kind="document")
    assert len(result.vectors) == 4
    assert provider.client.embed.call_count == 2
    assert len(provider.client.embed.call_args_list[0].kwargs["texts"]) == 2
    assert len(provider.client.embed.call_args_list[1].kwargs["texts"]) == 2


@patch("time.sleep", return_value=None)
def test_voyage_embed_rate_limit_retry_and_exhaustion(mock_sleep):
    provider = VoyageEmbeddingProvider(api_key="test-api-key", model="voyage-4-lite", dimension=2)
    
    error_rl = voyage_errors.RateLimitError("Rate limit exceeded")
    provider.client.embed = MagicMock(side_effect=error_rl)
    provider.client.count_tokens = MagicMock(return_value=1)

    with pytest.raises(LLMRateLimitError):
        provider.embed(["test"], kind="query")
        
    assert provider.client.embed.call_count == 4
    assert mock_sleep.call_count == 3


def test_voyage_embed_auth_error_no_retry():
    provider = VoyageEmbeddingProvider(api_key="test-api-key", model="voyage-4-lite", dimension=2)
    
    error_auth = voyage_errors.AuthenticationError("Invalid API key")
    provider.client.embed = MagicMock(side_effect=error_auth)
    provider.client.count_tokens = MagicMock(return_value=1)

    with pytest.raises(LLMAuthError):
        provider.embed(["test"], kind="query")
        
    assert provider.client.embed.call_count == 1
