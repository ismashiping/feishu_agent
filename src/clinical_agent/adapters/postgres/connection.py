"""Explicit bounded engine lifecycle; never connect or migrate during import."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from pydantic import Field, SecretStr, StrictInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, Engine, create_engine

from clinical_agent.domain.models import MetadataText


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLINICAL_AGENT_DB_",
        env_file=None,
        hide_input_in_errors=True,
    )

    host: MetadataText = "127.0.0.1"
    port: Annotated[StrictInt, Field(ge=1, le=65535)] = 55432
    name: Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")] = "clinical_agent"
    user: MetadataText = "clinical_agent"
    password: Annotated[SecretStr, Field(min_length=1, repr=False)]

    @field_validator("port", mode="before")
    @classmethod
    def parse_decimal_environment_port(cls, value: object) -> object:
        if isinstance(value, str) and value.isascii() and value.isdecimal():
            return int(value)
        return value


@contextmanager
def database_engine(settings: DatabaseSettings) -> Iterator[Engine]:
    settings = DatabaseSettings.model_validate(settings)
    url = URL.create(
        "postgresql+psycopg",
        username=settings.user,
        password=settings.password.get_secret_value(),
        host=settings.host,
        port=settings.port,
        database=settings.name,
    )
    engine = create_engine(
        url,
        echo=False,
        hide_parameters=True,
        pool_size=5,
        max_overflow=0,
        pool_timeout=5,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 5,
            "options": "-c statement_timeout=10000 -c lock_timeout=2000 "
            "-c idle_in_transaction_session_timeout=10000 -c timezone=UTC",
        },
    )
    try:
        yield engine
    finally:
        engine.dispose()
