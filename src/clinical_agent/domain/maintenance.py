"""Explicit bounded online windows and staged knowledge rebuild requests."""

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from clinical_agent.domain.chunking import ChunkingPolicy
from clinical_agent.domain.models import DTO


class OnlineUpdateRequest(DTO):
    batch_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,60}$")
    query: str = Field(min_length=1, max_length=4000)
    date_from: date
    date_to: date
    staging_root: Path
    dry_run: bool = False

    @model_validator(mode="after")
    def window(self) -> Self:
        if not 0 <= (self.date_to - self.date_from).days <= 30:
            raise ValueError("window_must_be_1_to_31_days")
        return self

    def signature(self) -> str:
        data = [
            self.query,
            self.date_from.isoformat(),
            self.date_to.isoformat(),
            str(self.staging_root.resolve()),
        ]
        return hashlib.sha256(json.dumps(data).encode()).hexdigest()


class RebuildRequest(DTO):
    run_id: UUID
    policy: ChunkingPolicy = Field(default_factory=ChunkingPolicy)
