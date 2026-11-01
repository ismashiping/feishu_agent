"""Two real report calls; timing wrappers only forward to original implementations."""
import functools
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path('docs/acceptance/live-report-context-20261102')
ROOT.mkdir(parents=True, exist_ok=False)
for name in ['api', 'postgres']:
    c = json.loads(subprocess.check_output(['docker', 'inspect', f'clinical-agent-e2e-{name}-1'], text=True))[0]
    env = dict(x.split('=', 1) for x in c['Config']['Env'] if '=' in x)
    if name == 'api':
        for k, v in env.items():
            if k.startswith(('LLM_', 'OPENALEX_')) and v:
                os.environ[k] = v
    else:
        os.environ.update(CLINICAL_AGENT_DB_HOST='127.0.0.1', CLINICAL_AGENT_DB_PORT=c['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort'], CLINICAL_AGENT_DB_USER=env['POSTGRES_USER'], CLINICAL_AGENT_DB_PASSWORD=env['POSTGRES_PASSWORD'], CLINICAL_AGENT_DB_NAME='clinical_agent_test_governance_20261101_retry1')

from sqlalchemy import text
from clinical_agent.db.connection import DatabaseSettings, database_engine
from clinical_agent.rag.embedding import LocalModelConfig, load_local_embedder
from clinical_agent.integrations.llm import LLMSettings
from clinical_agent.integrations.openalex import OpenAlexSettings, OpenAlexClient
from clinical_agent.integrations.oa_fulltext import OAFulltextSource, fulltext_candidates
from clinical_agent.application.pico import PicoPlanner
from clinical_agent.application.openalex import OpenAlexRetrievalService
from clinical_agent.application.fulltext import FulltextService
from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.application.report import ReportBuilder
from clinical_agent.db.fulltext import PostgresFulltextStore
from clinical_agent.integrations.langchain_generation import LangChainAnswerGenerator
from clinical_agent.domain.research import QuestionRequest
from clinical_agent.research_runtime import open_research_service

state = {'run': 'startup', 'events': []}

def save():
    (ROOT / 'events.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf8')

def instrument(cls, method, label):
    original = getattr(cls, method)
    @functools.wraps(original)
    def measured(*args, **kwargs):
        event = {'run': state['run'], 'stage': label}
        start = time.monotonic()
        try:
            out = original(*args, **kwargs)
            event['status'] = 'ok'
            if label == 'planner_response':
                (ROOT / f"{state['run']}-raw-plan.json").write_text(out, encoding='utf8')
            if label == 'cache_load': event['hit'] = out is not None
            if label == 'cache_publish': event['chunks'] = len(args[3]['passages'])
            if label == 'download_parse':
                event.update(paper=args[1].openalex_id, candidates=len(fulltext_candidates(args[1])), units=len(out.units))
            if label in ('retrieval', 'fulltext_rag'):
                event.update(selected=len(out.hits), fulltext_papers=sum(bool(h.fulltext) for h in out.hits), passages=sum(len(h.fulltext) for h in out.hits), warnings=out.warnings)
                (ROOT / f"{state['run']}-{label}.json").write_text(out.model_dump_json(indent=2), encoding='utf8')
            if label == 'planning':
                (ROOT / f"{state['run']}-plan.json").write_text(out.model_dump_json(indent=2), encoding='utf8')
            if label == 'search_http': event.update(returned=len(out[0]), total=out[1])
            if label == 'report_review':
                (ROOT / f"{state['run']}-intermediate-report.json").write_text(out.model_dump_json(indent=2), encoding='utf8')
            if label == 'analysis':
                (ROOT / f"{state['run']}-analysis.json").write_text(out.model_dump_json(indent=2), encoding='utf8')
            return out
        except Exception as error:
            event.update(status='failed', error_type=type(error).__name__, code=getattr(error, 'code', None), basis=getattr(error, 'basis', None))
            if label == 'download_parse': event['paper'] = args[1].openalex_id
            raise
        finally:
            event['seconds'] = round(time.monotonic()-start, 3)
            state['events'].append(event)
            save()
            print(json.dumps(event), flush=True)
    setattr(cls, method, measured)

for cls, method, label in [
    (PicoPlanner,'plan','planning'),(OpenAlexClient,'search','search_http'),
    (OpenAlexRetrievalService,'retrieve','retrieval'),
    (LangChainAnswerGenerator,'screen_candidates','screening'),
    (LangChainAnswerGenerator,'extract','planner_response'),
    (FulltextService,'enrich','fulltext_rag'),(OAFulltextSource,'fetch_record','download_parse'),
    (PostgresFulltextStore,'load','cache_load'),(PostgresFulltextStore,'publish','cache_publish'),
    (PostgresFulltextStore,'search','vector_search'),(EvidenceAnalyzer,'analyze','analysis'),
    (ReportBuilder,'build','report_review')]:
    instrument(cls, method, label)

# Only safe project messages; no HTTP headers/URLs or SDK exception text.
class SafeLog(logging.Handler):
    def emit(self, record):
        if record.name == 'clinical_agent.integrations.oa_fulltext':
            with (ROOT / 'candidate.log').open('a', encoding='utf8') as stream:
                stream.write(record.getMessage()+'\n')
handler=SafeLog()
logging.getLogger('clinical_agent.integrations.oa_fulltext').addHandler(handler)
logging.getLogger('clinical_agent.integrations.oa_fulltext').setLevel(logging.INFO)

start=time.monotonic()
embedder=load_local_embedder(LocalModelConfig(snapshot_dir=Path('models/multilingual-e5-base/d128750597153bb5987e10b1c3493a34e5a4502a')))
state['model_load_seconds']=round(time.monotonic()-start,3)
for method in ['embed_passages','embed_query']:
    instrument(type(embedder),method,method)
question='我想研究利用机器学习或深度学习模型，基于公开 ICU 临床数据预测患者发生急性肾损伤的风险。请分析目前是否已经有类似研究、已有研究主要采用哪些方法、可能存在什么研究差异，以及这个想法在数据、方法、算力和验证方面是否具有可行性。'
state['question']=question
state['results']=[]
with database_engine(DatabaseSettings()) as engine:
    def counts():
        with engine.connect() as c:
            return dict(indexes=c.scalar(text('select count(*) from oa_fulltext_indexes')), vectors=c.scalar(text('select count(*) from oa_fulltext_vectors')))
    state['before']=counts()
    with open_research_service(engine,embedder,LLMSettings(),OpenAlexSettings()) as service:
        state['limits']=service._limits.model_dump()
        for run in ['warm','repeat']:
            state['run']=run
            start=time.monotonic()
            result={'run':run,'before':counts()}
            try:
                output=service.report(QuestionRequest(request_id=uuid4(), question=question, scope='online'))
                (ROOT/f'{run}-report.json').write_text(output.model_dump_json(indent=2),encoding='utf8')
                (ROOT/f'{run}-report.md').write_text(output.markdown,encoding='utf8')
                result.update(status='returned',report_status=output.report.status,content_status=output.report.content_status)
            except Exception as e:
                result.update(status='failed',error_type=type(e).__name__,code=getattr(e,'code',None),details=getattr(e,'details',None))
            result.update(seconds=round(time.monotonic()-start,3),after=counts())
            state['results'].append(result)
            save()
            print(json.dumps(result),flush=True)



