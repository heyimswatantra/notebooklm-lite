import time

from google import genai
from google.genai import errors, types

from backend.llm.base import ChatMessage, ChatResult, LLMError, LLMRateLimitError, LLMAuthError


class GeminiChatProvider:
    """Chat provider using the Google Gemini SDK (generate_content API)."""

    def __init__(self, api_key: str, model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.0) -> ChatResult:
        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == "system":
                if system_instruction is None:
                    system_instruction = msg.content
                else:
                    system_instruction += "\n" + msg.content
            else:
                role = "user" if msg.role == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))
        
        config_kwargs = {"temperature": temperature}
        if system_instruction is not None:
            config_kwargs["system_instruction"] = system_instruction
            
        config = types.GenerateContentConfig(**config_kwargs)

        retries = 0
        max_retries = 3
        
        while True:
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config
                )
                
                text = response.text or ""
                prompt_tokens = 0
                completion_tokens = 0
                
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    prompt_tokens = response.usage_metadata.prompt_token_count or 0
                    completion_tokens = response.usage_metadata.candidates_token_count or 0
                
                return ChatResult(
                    text=text,
                    model=self.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens
                )
                
            except errors.ClientError as e:
                code = getattr(e, "code", None)
                if code == 429:
                    if retries < max_retries:
                        time.sleep(2 ** retries)
                        retries += 1
                        continue
                    raise LLMRateLimitError(f"Rate limit exceeded: {e}") from e
                elif code in (401, 403):
                    raise LLMAuthError(f"Authentication error: {e}") from e
                else:
                    raise LLMError(f"Client error: {e}") from e
            except errors.ServerError as e:
                if retries < max_retries:
                    time.sleep(2 ** retries)
                    retries += 1
                    continue
                raise LLMError(f"Server error: {e}") from e
            except errors.APIError as e:
                raise LLMError(f"API error: {e}") from e
