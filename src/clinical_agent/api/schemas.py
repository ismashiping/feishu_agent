"""HTTP request/response contracts and bounded API settings."""

from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from pydantic import DirectoryPath, Field, StringConstraints, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from clinical_agent.domain.ingestion import BatchIngestionResult
from clinical_agent.domain.models import DTO
from clinical_agent.domain.retrieval import RetrievalRequest


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLINICAL_AGENT_API_",
        env_file=None,
        hide_input_in_errors=True,
        extra="forbid",
        revalidate_instances="always",
    )
    model_dir: DirectoryPath
    import_root: DirectoryPath
    snapshot_dir: Path
    max_in_flight: Annotated[int, Field(strict=True, ge=1, le=4)] = 2
    max_request_bytes: Annotated[int, Field(strict=True, ge=1, le=65536)] = 16384

    @field_validator("max_in_flight", "max_request_bytes", mode="before")
    @classmethod
    def parse_environment_integer(cls, value: object) -> object:
        return (
            int(value)
            if isinstance(value, str) and value.isascii() and value.isdecimal()
            else value
        )


class ImportBody(DTO):
    source_type: Literal["pdf"]
    relative_path: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=512)]

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        if (
            value.startswith("/")
            or any(char in value for char in ("\\", ":", "\0"))
            or any(part in {"", ".", ".."} for part in value.split("/"))
        ):
            raise ValueError("Only bounded relative source paths are accepted")
        return value


class QuestionBody(RetrievalRequest):
    scope: Literal["online", "hybrid"] = "hybrid"


class ImportResponse(DTO):
    request_id: UUID
    result: BatchIngestionResult


class ApiError(DTO):
    request_id: UUID
    error_code: str
    message: str
    retryable: bool


class HealthReport(DTO):
    request_id: UUID
    status: Literal["ok", "not_ready"]
    scope: Literal["process", "runtime"]
