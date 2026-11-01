import json,os,sys,subprocess
from pathlib import Path
from dotenv import dotenv_values
from importlib.metadata import version
from sqlalchemy import text
from clinical_agent.db.connection import DatabaseSettings,database_engine
for k,v in dotenv_values('.artifacts/docker-e2e/compose.env').items():
 if v is not None:os.environ[k]=v
container=json.loads(subprocess.check_output(['docker','inspect','clinical-agent-e2e-postgres-1'],text=True))[0]
os.environ.update(CLINICAL_AGENT_DB_HOST='127.0.0.1',CLINICAL_AGENT_DB_PORT=container['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort'],CLINICAL_AGENT_DB_NAME='clinical_agent_test_context_20261102')
result={'python':sys.version,'packages':{p:version(p) for p in ['pytest','ruff','mypy','httpx','pydantic','SQLAlchemy','pgvector','alembic','sentence-transformers','torch','llama-index-core','langchain-openai','langgraph']},'llm_key_present':bool(os.environ.get('LLM_API_KEY')),'openalex_key_present':bool(__import__('clinical_agent.integrations.openalex',fromlist=['OpenAlexSettings']).OpenAlexSettings().api_key),'test_database':os.environ['CLINICAL_AGENT_DB_NAME']}
with database_engine(DatabaseSettings()) as engine,engine.connect() as c:
 result.update(revision=c.scalar(text('select version_num from alembic_version')),pgvector=c.scalar(text("select extversion from pg_extension where extname='vector'")),index_count=c.scalar(text('select count(*) from oa_fulltext_indexes')),vector_count=c.scalar(text('select count(*) from oa_fulltext_vectors')))
Path('docs/acceptance/consolidated-20261102/environment.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('environment recorded; credentials not printed')
