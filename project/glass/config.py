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
    api_token: str | None = None  # Bearer token for API auth; None = open access
    db_path: str = "glass.db"
    host: str = "0.0.0.0"
    port: int = 7777

    # Multi-model verification: use a different backend/model for the consistency
    # checker than the generator. When set, the verifier runs on a separate model,
    # decoupling generation from verification. "Policy is a promise. Architecture
    # is a guarantee." — Juno discussion, HN Feb 2026
    verifier_backend: str | None = None   # "ollama" | "openrouter" | "claude" | None (same as generator)
    verifier_model: str | None = None     # Model name for verifier; None = use same model as backend default

    # Cloud confirmation gate: when True, cloud backends require explicit opt-in
    # before any data leaves the machine. IBM's "Bob" agent (HN Jan 2026) showed
    # that "always allow" without a gate is "absolutely bananas." Glass enforces
    # an architectural gate, not just a toggle.
    cloud_confirm_required: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", cls.ollama_base_url),
            ollama_model=os.environ.get("OLLAMA_MODEL", cls.ollama_model),
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY"),
            openrouter_model=os.environ.get("OPENROUTER_MODEL", cls.openrouter_model),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            claude_model=os.environ.get("CLAUDE_MODEL", cls.claude_model),
            api_token=os.environ.get("GLASS_API_TOKEN"),
            db_path=os.environ.get("GLASS_DB_PATH", cls.db_path),
            host=os.environ.get("GLASS_HOST", cls.host),
            port=int(os.environ.get("GLASS_PORT", str(cls.port))),
            verifier_backend=os.environ.get("GLASS_VERIFIER_BACKEND"),
            verifier_model=os.environ.get("GLASS_VERIFIER_MODEL"),
            cloud_confirm_required=os.environ.get("GLASS_CLOUD_CONFIRM", "").lower() in ("1", "true", "yes"),
        )

    def verifier_settings(self) -> "Settings":
        """Return a Settings copy with model overrides for the verifier.

        When GLASS_VERIFIER_BACKEND is set, the verifier uses a different
        backend/model than the generator. This decouples generation from
        verification — the first step toward actual independence.
        """
        if not self.verifier_backend:
            return self

        import copy
        vs = copy.copy(self)
        if self.verifier_model:
            # Override the model for whichever backend the verifier uses
            if self.verifier_backend == "ollama":
                vs.ollama_model = self.verifier_model
            elif self.verifier_backend == "openrouter":
                vs.openrouter_model = self.verifier_model
            elif self.verifier_backend == "claude":
                vs.claude_model = self.verifier_model
        return vs
