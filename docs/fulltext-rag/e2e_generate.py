"""Real generation replay of contexts captured by live-source/real-E5 E2E."""

import json
import os
import subprocess
from pathlib import Path
from time import monotonic

from clinical_agent.adapters.llm import LLMSettings, open_llm
from clinical_agent.domain.citations import parse_draft
from clinical_agent.domain.research import GenerationInput

out = Path("docs/fulltext-rag/e2e")
raw = subprocess.run(
    ["docker", "inspect", "clinical-agent-e2e-api-1"], capture_output=True, text=True, check=True
)
for item in json.loads(raw.stdout)[0]["Config"]["Env"]:
    key, _, value = item.partition("=")
    if key.startswith("LLM_") and value:
        os.environ.setdefault(key, value)
results = []
with open_llm(LLMSettings()) as generator:
    for label in ("abstract", "fulltext_cold"):
        context = GenerationInput.model_validate_json(
            (out / f"{label}-context.json").read_text(encoding="utf-8")
        )
        started = monotonic()
        try:
            raw = generator.generate(context, timeout_seconds=60.0)
            draft = parse_draft(raw, max_bytes=32000)
            (out / f"{label}-real-draft.json").write_text(
                draft.model_dump_json(indent=2), encoding="utf-8"
            )
            supplied = {e.chunk_id for e in context.evidence} | {
                p.chunk_id for e in context.evidence for p in e.fulltext
            }
            assert all(set(c.evidence_chunk_ids) <= supplied for c in draft.claims)
            from datetime import UTC, datetime
            from uuid import uuid4

            from clinical_agent.domain.citations import build_answer
            from clinical_agent.domain.models import EvidenceChunk, SourceMetadata
            from clinical_agent.domain.research import QuestionRequest
            from clinical_agent.domain.retrieval import (
                DocumentSummary,
                EvidenceHit,
                RetrievalResult,
            )

            saved = json.loads((out / f"{label}-answer.json").read_text(encoding="utf-8"))
            metadata = saved["sources"][0]
            data = {k: v for k, v in metadata.items() if k in DocumentSummary.model_fields}
            data.update(source_uri=metadata["source_url"], ingestion_time=datetime.now(UTC))
            document = DocumentSummary.model_validate(data)
            item = context.evidence[0]
            chunk = EvidenceChunk(
                chunk_id=item.chunk_id,
                document_id=document.document_id,
                text=item.text,
                location=item.location,
                embedding_info=None,
                source_metadata=SourceMetadata.model_validate(
                    {k: getattr(document, k) for k in SourceMetadata.model_fields}
                ),
            )
            retrieval = RetrievalResult(
                embedding_info=None,
                search_provenance=saved["search_provenance"],
                scope="online",
                options={"top_k": 1},
                hits=[
                    EvidenceHit(
                        chunk=chunk,
                        document=document,
                        score=1.0,
                        rank=1,
                        score_type="pubmed_rank",
                        fulltext=item.fulltext,
                    )
                ],
            )
            answer = build_answer(
                QuestionRequest(
                    request_id=uuid4(),
                    scope="online",
                    question=context.question,
                    options={"top_k": 1},
                ),
                retrieval,
                draft,
                generated_at=datetime.now(UTC),
            )
            (out / f"{label}-real-answer.json").write_text(
                answer.model_dump_json(indent=2), encoding="utf-8"
            )

            (out / f"{label}-real-draft.json").write_text(
                draft.model_dump_json(indent=2), encoding="utf-8"
            )
            result = {
                "case": label,
                "status": "passed",
                "claims": len(draft.claims),
                "seconds": round(monotonic() - started, 2),
                "citation_membership": "passed",
                "context_characters": len(context.model_dump_json()),
            }
        except Exception as error:
            result = {
                "case": label,
                "status": "failed",
                "error_type": type(error).__name__,
                "error_code": getattr(error, "code", "unclassified"),
            }
        results.append(result)
        print(json.dumps(result), flush=True)
(out / "real-generation-summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
