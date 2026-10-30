"""Real-source E2E in existing PostgreSQL, isolated schema; no container changes."""

import json
import os
import subprocess
from pathlib import Path
from time import monotonic
from uuid import uuid4

import httpx
from sqlalchemy import URL, create_engine, text

from clinical_agent.adapters.embedding import LocalModelConfig, load_local_embedder
from clinical_agent.adapters.llm import LLMSettings, open_llm
from clinical_agent.adapters.pmc_fulltext import PMCSource
from clinical_agent.adapters.postgres.fulltext import PostgresFulltextStore
from clinical_agent.adapters.postgres.governance import SourceGovernance
from clinical_agent.adapters.pubmed_online import open_pubmed
from clinical_agent.application.fulltext import FulltextService
from clinical_agent.application.pubmed import PubMedRetrievalService
from clinical_agent.application.research import ResearchService
from clinical_agent.domain.research import QuestionRequest

OUT = Path("docs/fulltext-rag/e2e")
OUT.mkdir(exist_ok=True)


def container(name):
    result = subprocess.run(["docker", "inspect", name], capture_output=True, check=True, text=True)
    return json.loads(result.stdout)[0]


def environment(info):
    return dict(v.split("=", 1) for v in info["Config"]["Env"] if "=" in v)


info = container("clinical-agent-e2e-postgres-1")
settings = environment(info)
app_settings = environment(container("clinical-agent-e2e-api-1"))
for key, value in app_settings.items():
    if key.startswith(("LLM_", "PUBMED_")) and value:
        os.environ.setdefault(key, value)
url = URL.create(
    "postgresql+psycopg",
    username=settings["POSTGRES_USER"],
    password=settings["POSTGRES_PASSWORD"],
    host="127.0.0.1",
    port=55432,
    database=settings["POSTGRES_DB"],
)
engine = create_engine(url)
schema = "fulltext_e2e_" + uuid4().hex
with engine.begin() as c:
    c.execute(text(f"CREATE SCHEMA {schema}"))
scoped = create_engine(url, connect_args={"options": f"-c search_path={schema},public"})
summary = {
    "source_mode": "verified real XML replay"
    if os.environ.get("FULLTEXT_E2E_REPLAY_SOURCE") == "1"
    else "live PMC",
    "schema_isolated": True,
    "generation": "real"
    if os.environ.get("FULLTEXT_E2E_REAL_LLM") == "1"
    else "deterministic test double",
    "cases": [],
}
try:
    # Execute the actual additive migration in a temporary schema, no production stamping.
    import importlib.util

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    spec = importlib.util.spec_from_file_location(
        "fulltext_migration", "alembic/versions/p1001_0008_fulltext.py"
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with scoped.begin() as c:
        with Operations.context(MigrationContext.configure(c)):
            migration.upgrade()
    print("migration: passed", flush=True)
    model_dir = Path("models/multilingual-e5-base/d128750597153bb5987e10b1c3493a34e5a4502a")
    embedder = load_local_embedder(LocalModelConfig(snapshot_dir=model_dir))
    print("real E5 loaded", flush=True)

    class CountingEmbedder:
        passage_calls = 0

        def count_tokens(self, value):
            return embedder.count_tokens(value)

        def embed_query(self, value):
            return embedder.embed_query(value)

        def embed_passages(self, values, *, deadline):
            self.passage_calls += 1
            return embedder.embed_passages(values, deadline=deadline)

    class CountingSource(PMCSource):
        calls = 0

        def fetch(self, pmid, deadline):
            self.calls += 1
            if os.environ.get("FULLTEXT_E2E_REPLAY_SOURCE") == "1":
                from clinical_agent.adapters.pmc_fulltext import parse_bioc

                raw = Path("tests/fixtures/pmc1790863.bioc.xml").read_bytes()
                return (
                    "PMC1790863",
                    "CC BY",
                    "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/PMC1790863/unicode",
                    raw,
                    parse_bioc(raw, "PMC1790863"),
                )
            return super().fetch(pmid, deadline)

    class CapturingGenerator:
        def __init__(self, generator):
            self.generator = generator
            self.contexts = []

        def generate(self, context, *, timeout_seconds):
            self.contexts.append(context.model_dump(mode="json"))
            if os.environ.get("FULLTEXT_E2E_REAL_LLM") == "1":
                return self.generator.generate(context, timeout_seconds=timeout_seconds)
            evidence = context.evidence[0]
            quote = evidence.fulltext[0].text if evidence.fulltext else evidence.text
            return json.dumps(
                {
                    "claims": [
                        {
                            "text": quote[:1200],
                            "kind": "evidence",
                            "evidence_chunk_ids": [str(evidence.chunk_id)],
                            "limitations": [],
                        }
                    ]
                }
            )

    import sys

    def trace_fulltext(frame, event, arg):
        if frame.f_code.co_filename.replace("\\", "/").endswith("application/fulltext.py"):
            if event == "exception":
                error = arg[1]
                print("FULLTEXT DIAGNOSTIC:", type(error).__name__, str(error)[:300], flush=True)
            return trace_fulltext
        return None

    if os.environ.get("FULLTEXT_E2E_TRACE") == "1":
        sys.settrace(trace_fulltext)
    with httpx.Client() as client, open_pubmed() as pubmed, open_llm(LLMSettings()) as gen:
        online = PubMedRetrievalService(pubmed, governance=SourceGovernance(engine))
        source = CountingSource(client)
        counter = CountingEmbedder()
        fulltext = FulltextService(source, PostgresFulltextStore(scoped), counter)
        generator = CapturingGenerator(gen)
        request = QuestionRequest(
            request_id=uuid4(),
            question="这篇研究使用了什么具体方法、如何验证，以及主要局限是什么？请区分摘要与全文证据。",
            scope="online",
            pubmed={"query": "17299597[PMID]", "max_results": 1},
            options={"top_k": 1},
        )
        for label, enhancer in [
            ("abstract", None),
            ("fulltext_cold", fulltext),
            ("fulltext_warm", fulltext),
        ]:
            start = monotonic()
            before = (source.calls, counter.passage_calls)
            answer = ResearchService(
                retriever=None, online_retriever=online, generator=generator, fulltext=enhancer
            ).answer(request)
            answer_data = answer.model_dump(mode="json")
            (OUT / f"{label}-answer.json").write_text(
                json.dumps(answer_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            context = generator.contexts[-1]
            (OUT / f"{label}-context.json").write_text(
                json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            passages = [p for e in context["evidence"] for p in e["fulltext"]]
            case = {
                "case": label,
                "status": answer.status,
                "seconds": round(monotonic() - start, 2),
                "context_characters": len(
                    json.dumps(context, ensure_ascii=False, separators=(",", ":"))
                ),
                "passages": len(passages),
                "sections": [p["section"] for p in passages],
                "downloads": source.calls - before[0],
                "passage_embedding_calls": counter.passage_calls - before[1],
                "warnings": answer.retrieval_warnings,
            }
            summary["cases"].append(case)
            print(json.dumps(case, ensure_ascii=False), flush=True)
            assert answer.status == "answered"
            assert {s.pmid for s in answer.sources} == {"17299597"}
            if label != "abstract":
                assert passages, "Fulltext silently fell back: inspect warnings"
                assert len(passages) <= 2
                assert all(p["pmid"] == "17299597" for p in passages)
                assert case["context_characters"] <= 24000
            if label == "fulltext_warm":
                assert case["downloads"] == case["passage_embedding_calls"] == 0
        with scoped.connect() as c:
            summary["persisted_chunks"] = c.execute(
                text("SELECT count(*) FROM fulltext_vectors")
            ).scalar_one()
        summary["status"] = "passed"
except Exception as error:
    summary["status"] = "failed"
    summary["error_type"] = type(error).__name__
    summary["error"] = (
        str(error)[:250] if isinstance(error, AssertionError) else "see sanitized console"
    )
    raise
finally:
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    scoped.dispose()
    with engine.begin() as c:
        c.execute(text(f"DROP SCHEMA {schema} CASCADE"))
    engine.dispose()
