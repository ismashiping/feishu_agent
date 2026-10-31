"""Compare migration against contracts captured from the Phase 0 worktree."""

import inspect
import json
import re
from pathlib import Path
from typing import get_type_hints

import pytest

BASELINE = json.loads(
    (Path(__file__).parents[1] / "fixtures/agents/phase0-contracts.json").read_text(
        encoding="utf-8"
    )
)


def relocated_type(value):
    """Only module locations and process-specific function addresses may differ."""
    return re.sub(r"0x[0-9a-fA-F]+(?=>)", "0xADDRESS", str(value)).replace(
        "clinical_agent.application.workflow", "clinical_agent.agents.state"
    ).replace("clinical_agent.application.agents", "clinical_agent.agents.nodes")


@pytest.mark.parametrize("planner", [False, True])
def test_complete_graph_topology(planner):
    from clinical_agent.application.research import ResearchService

    service = ResearchService(
        retriever=object(), generator=object(), planner=object() if planner else None
    )
    graph = service._graph.get_graph()
    assert {
        "nodes": sorted(graph.nodes),
        "edges": sorted([e.source, e.target, e.conditional] for e in graph.edges),
    } == BASELINE["graphs"][str(planner)]


def test_state_types_and_required_fields():
    from clinical_agent.agents.state import AgentPatch, AgentStep, WorkflowState

    # Added after Phase 0: the report node records its feedback decision for the router.
    added = {
        "WorkflowState": {
            "feedback_target": "typing.NotRequired[typing.Literal['methods', 'scout', 'stop']]"
        }
    }
    for contract in (AgentPatch, AgentStep, WorkflowState):
        assert {
            k: relocated_type(v) for k, v in get_type_hints(contract, include_extras=True).items()
        } == {
            k: relocated_type(v)
            for k, v in {
                **BASELINE["state"][contract.__name__],
                **added.get(contract.__name__, {}),
            }.items()
        }
    assert WorkflowState.__required_keys__ == {"request", "deadline"}
    assert AgentStep.__required_keys__ == {"role", "elapsed_seconds"}
    assert AgentPatch.__required_keys__ == set()


def test_public_signatures_and_api_unchanged():
    from clinical_agent.api import create_app
    from clinical_agent.application.research import ResearchService

    assert {
        name: relocated_type(inspect.signature(getattr(ResearchService, name)))
        for name in BASELINE["interfaces"]
    } == {name: relocated_type(value) for name, value in BASELINE["interfaces"].items()}
    assert create_app().openapi() == BASELINE["openapi"]


@pytest.mark.parametrize("module", ["agents", "agents.state", "agents.nodes", "agents.graph"])
def test_new_modules_import_without_optional_runtime(module, tmp_path):
    from tests.unit.test_package import test_package_import_is_isolated_and_quiet

    test_package_import_is_isolated_and_quiet("clinical_agent." + module, tmp_path)
