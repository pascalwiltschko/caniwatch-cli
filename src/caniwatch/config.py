"""Environment configuration and enforced local inference boundary."""

from ipaddress import ip_address
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CANIWATCH_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    tmdb_token: SecretStr = SecretStr("")
    tavily_api_key: SecretStr = SecretStr("")
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = Field(default="gemma4:e4b", min_length=1)

    @field_validator("ollama_url")
    @classmethod
    def local_only(cls, value: str) -> str:
        parts = urlsplit(value)
        try:
            local = ip_address(parts.hostname or "").is_loopback
            _ = parts.port
        except ValueError:
            local = False
        if (
            not local
            or parts.scheme not in {"http", "https"}
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.path not in {"", "/"}
        ):
            raise ValueError("Ollama must use a literal loopback IP without credentials or a path.")
        return value.rstrip("/")
