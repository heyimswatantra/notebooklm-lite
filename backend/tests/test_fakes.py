from backend.llm.base import ChatMessage, ChatResult, EmbedResult, ChatProvider, EmbeddingProvider
from tests.fakes import FakeChatProvider, FakeEmbeddingProvider

def test_fake_chat_provider_satisfies_protocol():
    provider: ChatProvider = FakeChatProvider()
    result = provider.chat([ChatMessage(role='user', content='hi')])
    assert isinstance(result, ChatResult)
    assert result.text == 'Hello from fake LLM'
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 5

def test_fake_chat_provider_records_inputs():
    provider = FakeChatProvider()
    msgs = [ChatMessage(role='user', content='test')]
    provider.chat(msgs, temperature=0.7)
    assert provider.last_messages == msgs
    assert provider.last_temperature == 0.7

def test_fake_embedding_provider_satisfies_protocol():
    provider: EmbeddingProvider = FakeEmbeddingProvider(dimension=4)
    result = provider.embed(['hello', 'world'], kind='document')
    assert isinstance(result, EmbedResult)
    assert len(result.vectors) == 2
    assert len(result.vectors[0]) == 4
    assert result.dimension == 4

def test_fake_embedding_provider_default_dimension():
    provider = FakeEmbeddingProvider()
    result = provider.embed(['test'], kind='query')
    assert len(result.vectors[0]) == 1024
    assert result.dimension == 1024
