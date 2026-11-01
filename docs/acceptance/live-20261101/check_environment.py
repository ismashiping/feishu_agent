import json, os, subprocess, sys, time
from pathlib import Path
from importlib.metadata import version
from urllib.parse import urlsplit
from dotenv import load_dotenv
load_dotenv('.env', override=False)
result={'python':sys.version.split()[0]}
for package in ['httpx','sqlalchemy','pgvector','alembic','sentence-transformers','langgraph','langchain-openai','llama-index-core']:
    try: result[package]=version(package)
    except Exception as e: result[package]=type(e).__name__
for name in ['api','postgres']:
    proc=subprocess.run(['docker','inspect',f'clinical-agent-e2e-{name}-1'],capture_output=True,text=True)
    if proc.returncode:
        result[name+'_inspect']='unavailable'
        continue
    container=json.loads(proc.stdout)[0]
    env=dict(x.split('=',1) for x in container['Config']['Env'] if '=' in x)
    if name=='api':
        for k,v in env.items():
            if k.startswith(('LLM_','OPENALEX_')) and v: os.environ[k]=v
    else:
        os.environ.update(CLINICAL_AGENT_DB_HOST='127.0.0.1',CLINICAL_AGENT_DB_PORT=container['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort'],CLINICAL_AGENT_DB_USER=env['POSTGRES_USER'],CLINICAL_AGENT_DB_PASSWORD=env['POSTGRES_PASSWORD'],CLINICAL_AGENT_DB_NAME='clinical_agent_test_governance_20261101_retry1')
from clinical_agent.integrations.llm import LLMSettings
try:
    settings=LLMSettings()
    result['llm']={'configuration_valid':True,'host':urlsplit(settings.base_url).hostname,'invoked':False,'billing':'not established; no model request sent'}
except Exception as e: result['llm']={'configuration_valid':False,'error_type':type(e).__name__}
result['openalex_key_present']=bool(os.environ.get('OPENALEX_API_KEY'))
from clinical_agent.db.connection import DatabaseSettings,database_engine
from sqlalchemy import text
try:
    with database_engine(DatabaseSettings()) as engine, engine.connect() as c:
        result['test_database']={'connected':True,'revision':c.scalar(text('select version_num from alembic_version')),'pgvector':c.scalar(text("select extversion from pg_extension where extname='vector'")),'cache_rows':c.scalar(text('select count(*) from oa_fulltext_indexes')),'vector_rows':c.scalar(text('select count(*) from oa_fulltext_vectors'))}
except Exception as e: result['test_database']={'connected':False,'error_type':type(e).__name__}
print(json.dumps(result),flush=True)
Path('docs/acceptance/live-20261101/environment.json').write_text(json.dumps(result,indent=2),encoding='utf8')
from clinical_agent.rag.embedding import LocalModelConfig,load_local_embedder
start=time.monotonic()
try:
    model=load_local_embedder(LocalModelConfig(snapshot_dir=Path('models/multilingual-e5-base/d128750597153bb5987e10b1c3493a34e5a4502a')))
    loaded=time.monotonic()
    vector=model.embed_query('Predict acute kidney injury from public ICU clinical data').vector
    result['e5']={'loaded':True,'load_seconds':loaded-start,'query_seconds':time.monotonic()-loaded,'dimension':len(vector)}
except Exception as e: result['e5']={'loaded':False,'error_type':type(e).__name__}
Path('docs/acceptance/live-20261101/environment.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({'e5':result['e5']}),flush=True)
