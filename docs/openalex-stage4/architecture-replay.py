"""Frozen genuine sources + cached architecture -> real model; not new discovery."""
import json
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4

from clinical_agent.adapters.llm import LLMSettings, open_llm
from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
from clinical_agent.adapters.postgres.fulltext import PostgresFulltextStore
from clinical_agent.application.oa_fulltext import SIGNATURE, rerank_passages
from clinical_agent.application.openalex import record_hit
from clinical_agent.application.research import ResearchService
from clinical_agent.domain.citations import build_answer, parse_draft
from clinical_agent.domain.fulltext import FulltextPassage
from clinical_agent.domain.research import QuestionRequest, ResearchAnswer
from clinical_agent.domain.retrieval import RetrievalOptions, RetrievalResult
from feishu.sender import render_answer

root = Path("/tmp/oa_architecture_20261029_1")
old = ResearchAnswer.model_validate_json((root / "source.json").read_text())
hits = [record_hit(s.openalex_record, old.generated_at).model_copy(update={"score":1/rank, "rank":rank})
        for rank,s in enumerate(old.sources,1)]
with database_engine(DatabaseSettings()) as engine:
    store = PostgresFulltextStore(engine, openalex=True)
    for h in hits:
        payload = store.load("doi:"+h.document.doi, SIGNATURE)
        if payload is not None:
            h.fulltext = rerank_passages([FulltextPassage.model_validate(p) for p in payload["passages"]], "MedSAM与nnU-Net有哪些区别？")
result = RetrievalResult(scope="online",options=RetrievalOptions(),embedding_info=None,hits=hits,search_provenance=old.search_provenance)
request = QuestionRequest(request_id=uuid4(),question="MedSAM与nnU-Net有哪些区别？",scope="online")
with open_llm(LLMSettings()) as model:
    context = ResearchService(retriever=object(),generator=model)._prepare({"request":request,"retrieval":result,"query_plan":old.query_plan,"deadline":monotonic()+60})["context"]
    (root/"context.json").write_text(context.model_dump_json(indent=2))
    raw=model.generate(context,timeout_seconds=50)
    (root/"draft.json").write_text(raw)
answer=build_answer(request,result,parse_draft(raw,max_bytes=32000),generated_at=datetime.now(UTC))
(root/"answer.json").write_text(answer.model_dump_json(indent=2))
(root/"answer.txt").write_text(render_answer(answer))
print(json.dumps({"status":answer.status,"sources":len(answer.sources),"sections":[c.section for c in answer.claims],"fresh_discovery":False},ensure_ascii=False))
