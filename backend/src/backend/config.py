import functools
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = 'postgresql://postgres:postgres@db:5432/notebooklm'
    CHAT_PROVIDER: str = 'gemini'
    EMBED_PROVIDER: str = 'voyage'
    CHAT_MODEL: str = 'gemini-3.8-flash'
    EMBED_MODEL: str = 'voyage-4-lite'
    EMBED_DIMENSION: int = 1024
    GEMINI_API_KEY: str = ''
    VOYAGE_API_KEY: str = ''

    model_config = SettingsConfigDict(env_file='.env', frozen=True)

@functools.lru_cache()
def get_settings() -> Settings:
    return Settings()
