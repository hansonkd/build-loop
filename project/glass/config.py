import os
from dataclasses import dataclass


@dataclass
class Settings:
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    openrouter_api_key: str | None = None
    openrouter_model: str = "anthropic/claude-sonnet-4"
    anthropic_api_key: str | None = None
    claude_model: str = "claude-sonnet-4-20250514"
    db_path: str = "glass.db"
    host: str = "0.0.0.0"
    port: int = 7777

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", cls.ollama_base_url),
            ollama_model=os.environ.get("OLLAMA_MODEL", cls.ollama_model),
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY"),
            openrouter_model=os.environ.get("OPENROUTER_MODEL", cls.openrouter_model),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            claude_model=os.environ.get("CLAUDE_MODEL", cls.claude_model),
            db_path=os.environ.get("GLASS_DB_PATH", cls.db_path),
            host=os.environ.get("GLASS_HOST", cls.host),
            port=int(os.environ.get("GLASS_PORT", str(cls.port))),
        )
