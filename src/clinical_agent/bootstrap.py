"""Assemble the current local runtime explicitly, without external clients."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID, uuid4

from clinical_agent.config import Settings, load_settings
from clinical_agent.logging_config import configure_logging


@dataclass(frozen=True)
class Runtime:
    settings: Settings
    request_id: UUID


@contextmanager
def open_runtime(
    settings: Settings | None = None, *, request_id: UUID | None = None
) -> Iterator[Runtime]:
    """Read configuration only on entry; no external resources exist in Phase 0."""
    selected_settings = settings if settings is not None else load_settings()
    configure_logging(selected_settings)
    yield Runtime(selected_settings, request_id if request_id is not None else uuid4())
