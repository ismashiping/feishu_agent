"""Show canonical imports and representative removed compatibility paths."""

from __future__ import annotations

import importlib

from clinical_agent.agents.state import WorkflowState
from clinical_agent.api import create_app
from clinical_agent.channels.feishu.events import EventPolicy
from clinical_agent.db.models import Base
from clinical_agent.rag.embedding import LocalModelConfig


def main() -> None:
    old_modules = (
        "clinical_agent.application.workflow",
        "clinical_agent.api_runtime",
        "clinical_agent.adapters.embedding",
        "feishu.events",
    )
    for module in old_modules:
        try:
            importlib.import_module(module)
        except ModuleNotFoundError:
            continue
        raise AssertionError(f"legacy module remains importable: {module}")

    assert WorkflowState.__required_keys__ == {"request", "deadline"}
    assert create_app().openapi()["info"]["title"] == "Clinical Literature Agent"
    assert "documents" in Base.metadata.tables
    EventPolicy(app_id="app_demo", bot_open_id="bot_demo")
    assert LocalModelConfig.model_fields["snapshot_dir"].is_required()

    print("canonical_imports=ok")
    print(f"database_tables={len(Base.metadata.tables)}")
    print(f"removed_imports={len(old_modules)}")


if __name__ == "__main__":
    main()
