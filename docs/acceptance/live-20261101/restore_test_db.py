import json,os,subprocess
from dotenv import dotenv_values
from sqlalchemy import text
from alembic import command
from alembic.config import Config
from clinical_agent.db.connection import DatabaseSettings,database_engine
for k,v in dotenv_values('.artifacts/docker-e2e/compose.env').items():
    if v is not None:os.environ[k]=v
c=json.loads(subprocess.check_output(['docker','inspect','clinical-agent-e2e-postgres-1'],text=True))[0]
os.environ['CLINICAL_AGENT_DB_HOST']='127.0.0.1'
os.environ['CLINICAL_AGENT_DB_PORT']=c['NetworkSettings']['Ports']['5432/tcp'][0]['HostPort']
name='clinical_agent_test_context_20261102'
with database_engine(DatabaseSettings()) as engine,engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
    if connection.scalar(text('select 1 from pg_database where datname=:n'),{'n':name}):
        raise RuntimeError('Dedicated database exists; refusing reset')
    connection.execute(text('CREATE DATABASE "'+name+'"'))
os.environ['CLINICAL_AGENT_DB_NAME']=name
with database_engine(DatabaseSettings()) as engine,engine.begin() as connection:
    config=Config('alembic.ini');config.attributes['connection']=connection
    command.upgrade(config,'head')
    print('test_database_revision',connection.scalar(text('select version_num from alembic_version')))
