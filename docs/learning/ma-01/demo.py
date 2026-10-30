"""Frozen real evidence replay, not fresh network/model or medical acceptance."""

import json
from pathlib import Path
from uuid import uuid4

from clinical_agent.application.agents import IdeaPlannerAgent, LiteratureScoutAgent
from clinical_agent.application.pico import PicoPlanner
from clinical_agent.application.pubmed import PubMedRetrievalService
from clinical_agent.application.workflow import WorkflowState
from clinical_agent.domain.pubmed import PubMedSearchResult
from clinical_agent.domain.research import QuestionRequest


def main():
    root = Path(__file__).resolve().parents[3] / "evaluation/minimal-v1/evidence"
    case = json.loads((root / "samples.json").read_text(encoding="utf-8"))[0]

    class RecordedExtractor:
        def extract(self, request, *, timeout_seconds):
            return (root / "model-response-3.txt").read_text(encoding="utf-8")

    class RecordedSearch:
        def search(self, request, *, timeout_seconds):
            return PubMedSearchResult.model_validate_json(
                (root / "blood-pressure-pubmed.json").read_text(encoding="utf-8")
            )

    class UnusedLocal:
        def retrieve(self, request):
            raise AssertionError("Online replay must not use local")

    state: WorkflowState = {
        "request": QuestionRequest(
            request_id=uuid4(), question=case["idea"], scope="online", options={"top_k": 2}
        ),
        "deadline": 10.0,
    }
    state.update(
        IdeaPlannerAgent(PicoPlanner(extractor=RecordedExtractor()), clock=lambda: 1.0)(state)
    )
    state.update(
        LiteratureScoutAgent(
            UnusedLocal(), online=PubMedRetrievalService(RecordedSearch()), clock=lambda: 1.0
        )(state)
    )
    print(
        json.dumps(
            {
                "mode": "frozen_replay_not_live_e2e",
                "roles": state["agent_steps"],
                "pmids": [h.document.pmid for h in state["retrieval"].hits],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
