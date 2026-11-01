import os,subprocess,sys
name="clinical-agent-governance-redis-20261101"
subprocess.run(["docker","run","--pull=never","--rm","-d","--name",name,"-p","127.0.0.1:56379:6379","redis:8.2.2-alpine"],check=True,stdout=subprocess.DEVNULL)
try:
    os.environ["CLINICAL_AGENT_TEST_REDIS_URL"]="redis://127.0.0.1:56379/0"
    code=subprocess.call([sys.executable,"-X","utf8","-m","pytest","tests/integration/test_feishu_dedup_redis.py","tests/integration/test_phase1_acceptance.py::test_real_redis_worker_sender_dedup_capacity_and_drain","-m","redis","-q","--tb=short","--basetemp=.artifacts/tmp/governance-redis","-o","cache_dir=.artifacts/tmp/governance-redis-cache"])
finally:
    subprocess.run(["docker","stop",name],check=True,stdout=subprocess.DEVNULL)
raise SystemExit(code)
