import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
DOCS_DIR = DATA_DIR / "documents"
VECTOR_DIR = DATA_DIR / "vectors"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Provider: "xiaomi", "openrouter", "ollama", or "fallback"
    LLM_PROVIDER: str = "xiaomi"

    # Xiaomi MiMo (platform.xiaomimimo.com)
    XIAOMI_API_KEY: str = ""
    XIAOMI_BASE_URL: str = "https://api.xiaomimimo.com/v1"
    XIAOMI_MODEL: str = "mimo-v2-pro"

    # OpenRouter (cloud, paid)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # Ollama (local, free)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    APP_NAME: str = "Mnemosyne AI"
    APP_URL: str = "http://localhost:8000"

    DEFAULT_CHAT_MODEL: str = "mimo-v2-pro"
    DEFAULT_REASONING_MODEL: str = "mimo-v2-pro"
    DEFAULT_CODING_MODEL: str = "mimo-v2-pro"
    DEFAULT_SUMMARY_MODEL: str = "mimo-v2-pro"

    REQUEST_TIMEOUT_SECONDS: int = 90
    MAX_HISTORY_MESSAGES: int = 12
    DEBUG: bool = True

    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    RAG_TOP_K: int = 5
    RAG_MAX_CHUNK_CHARS: int = 600
    RAG_CHUNK_OVERLAP: int = 100

    DATABASE_URL: str = f"sqlite:///{(DATA_DIR / 'mnemosyne.db').as_posix()}"
    BACKGROUND_JOB_MODE: str = "fastapi"
    VECTOR_BACKEND: str = "chroma"

    @property
    def active_provider(self) -> str:
        if self.LLM_PROVIDER != "fallback":
            return self.LLM_PROVIDER
        if self.XIAOMI_API_KEY:
            return "xiaomi"
        if self.OPENROUTER_API_KEY:
            return "openrouter"
        return "fallback"


settings = Settings()
