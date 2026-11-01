import json,os,subprocess,sys
from pathlib import Path
container=json.loads(subprocess.check_output(["docker","inspect","clinical-agent-e2e-api-1"],text=True))[0]
for item in container["Config"]["Env"]:
    key,sep,value=item.partition("=")
    if key.startswith(("LLM_","OPENALEX_")) and value:os.environ[key]=value
os.environ["CLINICAL_AGENT_TEST_EVIDENCE_DIR"]=str(Path(".artifacts/governance").resolve())
raise SystemExit(subprocess.call([sys.executable,"-X","utf8","-m","pytest","tests/integration/test_research_live.py","-m","external","-q","--tb=short","--basetemp=.artifacts/tmp/governance-llm","-o","cache_dir=.artifacts/tmp/governance-live-cache"]))
