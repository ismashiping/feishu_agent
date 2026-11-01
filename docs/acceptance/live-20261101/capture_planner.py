import json,os,subprocess
from pathlib import Path
from clinical_agent.integrations.llm import LLMSettings,open_llm
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.application.pico import PicoPlanner
root=Path('docs/acceptance/planner-20261101');root.mkdir(exist_ok=True)
c=json.loads(subprocess.check_output(['docker','inspect','clinical-agent-e2e-api-1'],text=True))[0]
for item in c['Config']['Env']:
    k,_,v=item.partition('=')
    if k.startswith('LLM_') and v:os.environ[k]=v
q=json.loads(Path('docs/acceptance/live-report-20261101/events.json').read_text(encoding='utf8'))['question']
with open_llm(LLMSettings()) as model:
    original=model.extract
    def capture(request,**kwargs):
        raw=original(request,**kwargs)
        (root/'raw-before.json').write_text(raw,encoding='utf8')
        return raw
    model.extract=capture
    try:
        plan=PicoPlanner(extractor=model).plan(ClassificationRequest(question=q))
        (root/'plan-before.json').write_text(plan.model_dump_json(indent=2),encoding='utf8')
        print('plan accepted')
    except Exception as e:print(type(e).__name__,getattr(e,'code',None))
