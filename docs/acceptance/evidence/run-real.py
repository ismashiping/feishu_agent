import os, subprocess, sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(".env", override=False)
from clinical_agent.db.connection import DatabaseSettings, database_engine
from sqlalchemy import text
from alembic.config import Config
from alembic import command
import json
container=json.loads(subprocess.check_output(["docker","inspect","clinical-agent-e2e-postgres-1"],text=True))[0]
env=dict(item.split("=",1) for item in container["Config"]["Env"] if "=" in item)
os.environ["CLINICAL_AGENT_DB_PASSWORD"]=env["POSTGRES_PASSWORD"]
os.environ["CLINICAL_AGENT_DB_USER"]=env["POSTGRES_USER"]
os.environ["CLINICAL_AGENT_DB_NAME"]=env["POSTGRES_DB"]
os.environ["CLINICAL_AGENT_DB_HOST"]="127.0.0.1"
os.environ["CLINICAL_AGENT_DB_PORT"]=container["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
settings=DatabaseSettings()
assert settings.host == "127.0.0.1"
name="clinical_agent_test_governance_20261101_retry1"
with database_engine(settings) as engine:
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        exists=connection.scalar(text("SELECT 1 FROM pg_database WHERE datname=:name"), {"name":name})
        if exists:
            raise RuntimeError("Dedicated database already exists; do not reset unknown data")
        connection.execute(text('CREATE DATABASE "'+name+'"'))
os.environ["CLINICAL_AGENT_DB_NAME"]=name
os.environ["CLINICAL_AGENT_DB_ALLOW_TEST_RESET"]="1"
os.environ["CLINICAL_AGENT_TEST_EVIDENCE_DIR"]=str(Path(".artifacts/governance").resolve())
with database_engine(DatabaseSettings()) as engine:
    with engine.begin() as connection:
        config=Config("alembic.ini"); config.attributes["connection"]=connection
        command.upgrade(config,"head")
    with engine.connect() as connection:
        revision=connection.scalar(text("SELECT version_num FROM alembic_version"))
        assert revision=="oa3003_0011"
        print("Dedicated database migrated to",revision,flush=True)
args=[sys.executable,"-X","utf8","-m","pytest","tests/integration/test_api_pipeline.py","tests/integration/test_command_pipeline.py","-m","database","-q","--tb=short","-o","cache_dir=.artifacts/tmp/governance-real-cache","--basetemp=.artifacts/tmp/governance-real"]
raise SystemExit(subprocess.call(args))
