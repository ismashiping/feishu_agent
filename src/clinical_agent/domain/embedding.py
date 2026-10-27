"""Validated vectors and their evidence identity, independent of model libraries."""

import math
from typing import Annotated, Self

from pydantic import Field, StrictFloat, field_validator, model_validator

from clinical_agent.domain.models import DTO, EmbeddingInfo, EvidenceChunk

Vector = list[Annotated[StrictFloat, Field(allow_inf_nan=False)]]


def _validate_vector(vector: list[float], info: EmbeddingInfo) -> None:
    if len(vector) != info.dimension:
        raise ValueError("Vector dimension must match the declared model identity")
    norm = math.sqrt(sum(value * value for value in vector))
    if not math.isfinite(norm) or norm == 0 or (info.normalized and abs(norm - 1.0) > 1e-4):
        raise ValueError("Vector must be nonzero and match its normalization declaration")


class _VectorDTO(DTO):
    vector: Vector

    @field_validator("vector", mode="before")
    @classmethod
    def require_float_values(cls, value: object) -> object:
        if not isinstance(value, list) or any(type(element) is not float for element in value):
            raise ValueError("Vector must contain explicit floating point values")
        return value


class EmbeddedChunk(_VectorDTO):
    evidence: EvidenceChunk

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if self.evidence.embedding_info is None:
            raise ValueError("Encoded evidence requires an embedding identity")
        _validate_vector(self.vector, self.evidence.embedding_info)
        return self


class QueryEmbedding(_VectorDTO):
    embedding_info: EmbeddingInfo

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        _validate_vector(self.vector, self.embedding_info)
        return self
