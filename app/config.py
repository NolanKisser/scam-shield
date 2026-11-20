from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODELS = {"anthropic": "claude-opus-5-5", "openai": "gpt-4o-mini"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Model provider:
    #   "anthropic": Claude via the Anthropic SDK (ANTHROPIC_API_KEY or `ant auth login`)
    #   "openai":    any OpenAI-compatible Chat Completions endpoint: OpenAI, Gemini,
    #                OpenRouter, Groq, Together, Mistral, Ollama, LM Studio, vLLM, ...
    llm_provider: str = "anthropic"
    llm_model: str = Field("", validation_alias=AliasChoices("llm_model", "claude_model"))
    llm_base_url: str = "https://api.openai.com/v1"  # openai provider only
    llm_api_key: str = ""  # openai provider only; blank for local servers like Ollama
    # Claude only; blank omits it (for models that don't support effort)
    llm_effort: str = Field("low", validation_alias=AliasChoices("llm_effort", "claude_effort"))
    llm_timeout_s: float = 20.0

    # Optional reputation APIs (collectors skip themselves when unset)
    google_safe_browsing_key: str = ""
    urlhaus_auth_key: str = ""

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    validate_twilio_signature: bool = True
    public_base_url: str = ""  # e.g. https://abcd.ngrok.app (needed for signature checks + callbacks)

    # Guardian links: "protected:guardian,protected2:guardian2" (E.164 numbers)
    guardians: str = ""
    guardian_alert_threshold: float = 0.8

    collector_timeout_s: float = 2.0

    @property
    def model(self) -> str:
        return self.llm_model or DEFAULT_MODELS.get(self.llm_provider, "")

    def guardian_map(self) -> dict[str, str]:
        pairs = [p.split(":", 1) for p in self.guardians.split(",") if ":" in p]
        return {a.strip(): b.strip() for a, b in pairs}


settings = Settings()
