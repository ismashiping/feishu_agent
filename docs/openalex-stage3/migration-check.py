import json,sys
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from clinical_agent.adapters.postgres.connection import DatabaseSettings,database_engine
root=Path(sys.argv[1]);settings=DatabaseSettings();assert settings.name.startswith('clinical_agent_test_oa_stage3_')
config=Config(str(root/'alembic.ini'))
with database_engine(settings) as engine:
 with engine.begin() as c:
  c.execute(text("INSERT INTO fulltext_indexes(pmid,signature,payload,expires_at) VALUES ('__stage3_test__','test','{}',now()+interval '1 day')"))
 with engine.begin() as c:
  config.attributes['connection']=c;command.downgrade(config,'p1001_0008')
  assert c.scalar(text("SELECT to_regclass('oa_fulltext_indexes')")) is None
  assert c.scalar(text("SELECT count(*) FROM fulltext_indexes WHERE pmid='__stage3_test__'"))==1
 with engine.begin() as c:
  config.attributes['connection']=c;command.upgrade(config,'head')
  assert c.scalar(text("SELECT version_num FROM alembic_version"))=='oa3001_0009'
  assert c.scalar(text("SELECT count(*) FROM oa_fulltext_indexes"))==0
 result={'database':settings.name,'downgrade_verified':True,'legacy_sentinel_preserved':True,'reupgrade_verified':True,'business_database_modified':False}
(root/'migration-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
