import json,time
from pathlib import Path
import httpx
from clinical_agent.integrations.openalex import OpenAlexClient
from clinical_agent.integrations.oa_fulltext import fulltext_candidates
start=time.monotonic()
result={'entry':'OpenAlexClient.search (diagnostic only; not planned or model-screened)','query':'acute kidney injury machine learning MIMIC ICU','authenticated':False}
try:
    with httpx.Client() as http:
        records,total,warnings=OpenAlexClient(http).search(result['query'],date_from=None,date_to=None,sort='relevance_score:desc',timeout_seconds=20)
    result.update(returned=len(records),total=total,warnings=warnings,works=[{'id':r.openalex_id,'title':r.title,'doi':r.doi,'abstract_status':r.abstract_status,'candidate_count':len(fulltext_candidates(r))} for r in records])
    for record in records: record.verify_snapshot()
    result['snapshot_check']='passed'
except Exception as e:
    result.update(error_type=type(e).__name__,error_code=getattr(e,'code','unavailable'))
result['seconds']=time.monotonic()-start
Path('docs/acceptance/live-20261101/openalex.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
