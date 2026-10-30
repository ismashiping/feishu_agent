"""Explicit local update batches; cursors bind to an ordered scope."""

import hashlib
import json
from pathlib import Path
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from clinical_agent.domain.models import DTO


class UpdateRequest(DTO):
    batch_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    allowed_root: Path
    files: list[str] = Field(min_length=1, max_length=100)
    source_type: Literal["pdf", "pubmed_xml"]
    dry_run: bool = False
    rescan: bool = False
    window_label: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def safe_paths(self) -> Self:
        if len(self.files) != len(set(self.files)):
            raise ValueError("Duplicate input paths")
        for name in self.files:
            if (
                name.startswith("/")
                or any(c in name for c in ["\\", ":", "\x00"])
                or any(p in {"", ".", ".."} for p in name.split("/"))
            ):
                raise ValueError("Relative paths must stay within the allowed root")
        return self

    def signature(self) -> str:
        return hashlib.sha256(
            json.dumps(
                [str(self.allowed_root.resolve()), self.files, self.source_type, self.window_label],
                ensure_ascii=False,
            ).encode()
        ).hexdigest()


class UpdateResult(DTO):
    scope_hash: str = ""
    source_scope: Literal["local"] = "local"
    window_label: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    run_id: UUID
    status: Literal["completed", "failed", "dry_run", "running"]
    cursor_before: int
    cursor_after: int
    items: list[dict[str, object]]
    evaluation_status: Literal["not_run", "passed", "not_accepted", "failed"] = "not_run"
