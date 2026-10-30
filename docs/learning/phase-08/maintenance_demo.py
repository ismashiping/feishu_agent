"""Offline request-contract demo; no database, model or network access."""

from datetime import date
from pathlib import Path
from uuid import uuid4

from clinical_agent.domain.chunking import ChunkingPolicy
from clinical_agent.domain.maintenance import OnlineUpdateRequest, RebuildRequest

window = OnlineUpdateRequest(
    batch_id="demo-window",
    query="26551272[uid]",
    date_from=date(2015, 11, 1),
    date_to=date(2015, 11, 30),
    staging_root=Path(".research-cache/demo"),
    dry_run=True,
)
rebuild = RebuildRequest(run_id=uuid4(), policy=ChunkingPolicy(max_tokens=256))
assert len(window.signature()) == 64
assert rebuild.policy.max_tokens == 256
print("Bounded window and explicit rebuild contracts validated; no services called.")
