import json,os,subprocess
from pathlib import Path
from dotenv import dotenv_values
from sqlalchemy import text
from clinical_agent.db.connection import DatabaseSettings,database_engine
from clinical_agent.db.fulltext import PostgresFulltextStore
from clinical_agent.application.oa_fulltext import SIGNATURE
from clinical_agent.domain.fulltext import paper_key
from clinical_agent.domain.openalex import OpenAlexRecord
for k,v in dotenv_values('.artifacts/docker-e2e/compose.env').items():
    if v is not None:os.environ[k]=v
c=json.loads(subprocess.check_output(['docker','inspect','clinical-agent-e2e-postgres-1'],text=True))[0]
os.environ.update(CLINICAL_AGENT_DB_HOST='127.0.0.1',CLINICAL_AGENT_DB_PORT=c['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort'],CLINICAL_AGENT_DB_NAME='clinical_agent_test_context_20261102')
root=Path('docs/acceptance/live-report-context-restored-20261102')
result={}
with database_engine(DatabaseSettings()) as engine:
 store=PostgresFulltextStore(engine,openalex=True)
 with engine.connect() as conn:
    rows=conn.execute(text("select paper_key, signature=:sig as signature_matches, expires_at>now() as unexpired, jsonb_array_length(payload->'passages') as passages, (select count(*) from oa_fulltext_vectors v where v.paper_key=i.paper_key) as vectors from oa_fulltext_indexes i"),{'sig':SIGNATURE}).mappings().all()
    result['rows']=[dict(row) for row in rows]
 for run in ['cold','repeat']:
    retrieval=json.loads((root/f'{run}-fulltext_rag.json').read_text(encoding='utf8'))
    checks=[]
    for h in retrieval['hits']:
        record=OpenAlexRecord.model_validate(h['document']['openalex_record'])
        key=paper_key(record);payload=store.load(key,SIGNATURE)
        checks.append({'key':key,'openalex_id':record.openalex_id,'now_load_hit':payload is not None,'run_fulltext_passages':len(h['fulltext'])})
    result[run]=checks
Path('docs/acceptance/cache-review-diagnosis-20261102').mkdir(exist_ok=True)
Path('docs/acceptance/cache-review-diagnosis-20261102/cache-readback.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
