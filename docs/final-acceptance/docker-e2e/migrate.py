import os
from dotenv import dotenv_values
from alembic.config import Config
from alembic import command
for k,v in dotenv_values('.artifacts/docker-e2e/compose.env').items():
 if k.startswith('CLINICAL_AGENT_DB_') and v:os.environ[k]=v
command.upgrade(Config('alembic.ini'),'head')
