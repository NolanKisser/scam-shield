from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Claude. The SDK also picks up ANTHROPIC_API_KEY / `ant auth login` on its own.
    claude_model: str = "claude-opus-5-5"
    claude_effort: str = "low"  # low keeps SMS replies fast; raise for harder cases

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

    def guardian_map(self) -> dict[str, str]:
        pairs = [p.split(":", 1) for p in self.guardians.split(",") if ":" in p]
        return {a.strip(): b.strip() for a, b in pairs}


settings = Settings()
