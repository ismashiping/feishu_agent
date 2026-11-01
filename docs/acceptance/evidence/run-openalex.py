import json,os,subprocess,sys
from pathlib import Path
container=json.loads(subprocess.check_output(["docker","inspect","clinical-agent-e2e-api-1"],text=True))[0]
for item in container["Config"]["Env"]:
    key,sep,value=item.partition("=")
    if key.startswith(("LLM_","OPENALEX_")) and value:os.environ[key]=value
os.environ["CLINICAL_AGENT_TEST_EVIDENCE_DIR"]=str(Path(".artifacts/governance").resolve())
from clinical_agent.integrations.openalex import open_openalex
from clinical_agent.integrations.oa_fulltext import OAFulltextSource, AcquisitionError
from time import monotonic
import httpx
with open_openalex() as source:
    records,total,warnings=source.search("MedSAM",date_from=None,date_to=None,sort="relevance_score:desc",timeout_seconds=20)
assert records
for record in records:record.verify_snapshot()
result={"records":len(records),"total":total,"warnings":warnings,"identity_snapshots":"passed","fulltext":"not acquired"}
with httpx.Client(trust_env=False) as client:
    source=OAFulltextSource(client,api_key=os.environ.get("OPENALEX_API_KEY"))
    deadline=monotonic()+50
    for record in records[:2]:
        try:
            acquired=source.fetch_record(record,deadline,[0])
            units=acquired[3]
            assert units
            result.update(fulltext="acquired and parsed",paper=record.openalex_id,units=len(units))
            break
        except (AcquisitionError, ValueError) as error:
            result.setdefault("acquisition_errors",[]).append(str(error))
Path(".artifacts/governance/openalex-result.json").write_text(json.dumps(result,indent=2),encoding="utf8")
print(json.dumps(result))
raise SystemExit(0 if result["fulltext"]=="acquired and parsed" else 1)
