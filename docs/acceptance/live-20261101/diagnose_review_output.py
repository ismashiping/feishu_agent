import json,os,time,logging
from pathlib import Path
from dotenv import dotenv_values
from clinical_agent.integrations.llm import LLMSettings,open_llm
root=Path('docs/acceptance/review-output-budget-20261102');root.mkdir(exist_ok=False)
for k,v in dotenv_values('.artifacts/docker-e2e/compose.env').items():
    if v is not None:os.environ[k]=v
old=Path('docs/acceptance/final-live-20261102')
context=json.loads(next(old.glob('first-review-input-*.json')).read_text(encoding='utf8'))
result={'claims':len(context['claims'])}
class SafeLog(logging.Handler):
    def emit(self, record):
        if getattr(record,'evidence_stage',None)=='provider':
            result['provider']={k:getattr(record,k,None) for k in ['failure_kind','evidence_counts']}
handler=SafeLog();logger=logging.getLogger('clinical_agent.application.openalex');logger.addHandler(handler);logger.setLevel(logging.INFO)
settings=LLMSettings();result['max_tokens']=settings.max_tokens
start=time.monotonic()
with open_llm(settings) as model:
    try:
        raw=model.review_claims(context,timeout_seconds=60)
        (root/'before-response.json').write_text(raw,encoding='utf8')
        result['status']='returned'
    except Exception as e:result.update(status='failed',code=getattr(e,'code',None),details=getattr(e,'details',None))
result['seconds']=time.monotonic()-start
(root/'before-diagnostic.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
