"""Explicit configuration for the current offline engineering scaffold."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read only supported environment settings when explicitly constructed."""

    model_config = SettingsConfigDict(
        env_prefix="CLINICAL_AGENT_",
        case_sensitive=False,
        env_file=None,
        hide_input_in_errors=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


def load_settings() -> Settings:
    """Construct fresh settings; do not cache or implicitly read a dotenv file."""
    return Settings()
