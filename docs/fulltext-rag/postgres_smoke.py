"""Opt-in PostgreSQL fulltext adapter check in an isolated temporary schema."""
import json
import subprocess
from uuid import uuid4

from sqlalchemy import create_engine, text
from clinical_agent.adapters.postgres.fulltext import PostgresFulltextStore

raw = subprocess.run(['docker','inspect','clinical-agent-e2e-postgres-1'],
                     capture_output=True, check=True, text=True)
container = json.loads(raw.stdout)[0]
values = dict(item.split('=',1) for item in container['Config']['Env'] if '=' in item)
from sqlalchemy import URL
url = URL.create('postgresql+psycopg', username=values['POSTGRES_USER'],
    password=values['POSTGRES_PASSWORD'], host='127.0.0.1', port=55432,
    database=values['POSTGRES_DB'])
engine = create_engine(url)
schema = 'fulltext_smoke_' + uuid4().hex
with engine.begin() as c:
    c.execute(text(f'CREATE SCHEMA {schema}'))
scoped = create_engine(url, connect_args={'options': f'-c search_path={schema},public'})
try:
    with scoped.begin() as c:
        c.execute(text('CREATE TABLE fulltext_indexes (pmid text PRIMARY KEY, signature text NOT NULL, payload jsonb NOT NULL, expires_at timestamptz NOT NULL)'))
        c.execute(text('CREATE TABLE fulltext_vectors (chunk_id uuid PRIMARY KEY, pmid text REFERENCES fulltext_indexes(pmid), payload jsonb NOT NULL, embedding vector(768) NOT NULL)'))
    store = PostgresFulltextStore(scoped)
    payload = {'content_hash':'abc','passages':[{'chunk_id':str(uuid4()),'text':'Methods: k-means'}]}
    vector = [1.] + [0.]*767
    store.publish('17299597','test-v1',payload,[vector])
    assert store.load('17299597','test-v1') == payload
    assert store.load('17299597','test-v2') is None
    assert store.search('17299597',vector) == payload['passages']
    assert store.search('999999',vector) == []
    assert store.reuse_content('17299597','test-v1','abc')
    try:
        store.publish('17299597','test-v1',payload,[])
    except ValueError:
        pass
    else:
        raise AssertionError('partial publication accepted')
    assert store.search('17299597',vector) == payload['passages']
    print('PASS: publish, scoped search, cache reuse, signature invalidation, rollback')
finally:
    scoped.dispose()
    with engine.begin() as c:
        c.execute(text(f'DROP SCHEMA {schema} CASCADE'))
    engine.dispose()
