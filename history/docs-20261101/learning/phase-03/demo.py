"""Offline PICO provenance demo; fixed extraction is not model accuracy evidence."""

import json

from clinical_agent.application.pico import PicoPlanner
from clinical_agent.domain.pico import ClassificationRequest


class FixedExtractor:
    def extract(self, request: ClassificationRequest, *, timeout_seconds: float) -> str:
        return json.dumps(
            {
                "question_type": "intervention",
                "pico": {
                    "population": {
                        "text": "Adults",
                        "origin": "user_text",
                        "source_span": {"start": 0, "end": 6},
                    },
                    "intervention": None,
                    "comparison": None,
                    "outcome": None,
                },
                "terms": [],
                "ambiguities": [],
            }
        )


if __name__ == "__main__":
    plan = PicoPlanner(extractor=FixedExtractor()).plan(
        ClassificationRequest(question="Adults: what evidence is available?")
    )
    print(plan.model_dump_json())
