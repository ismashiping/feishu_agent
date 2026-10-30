import json,logging,time
from pathlib import Path
from clinical_agent.adapters.llm import LLMSettings,open_llm
from clinical_agent.application.pico import PicoPlanner
from clinical_agent.domain.pico import ClassificationRequest
from clinical_agent.domain.research import ResearchError
q='Are there studies on intratumoral subregion delineation in liver tumors? What representative papers exist, and what methods do they use to define these subregions?'
result={'calls':0,'diagnostics':[]}
class Handler(logging.Handler):
 def emit(self,record):
  if hasattr(record,'extraction_diagnostic'):result['diagnostics'].append(record.extraction_diagnostic)
logging.getLogger('clinical_agent.application.pico').addHandler(Handler())
with open_llm(LLMSettings()) as gen:
 original=gen._model
 class Model:
  def invoke(self,*a,**kw):
   result['calls']+=1
   msg=original.invoke(*a,**kw);result['usage']=msg.usage_metadata
   return msg
 gen._model=Model()
 class Extractor:
  def extract(self,*a,**kw):
   raw=gen.extract(*a,**kw)
   Path('/tmp/plan-a-english-response.json').write_text(raw,encoding='utf-8')
   return raw
 start=time.monotonic()
 try:result['plan']=PicoPlanner(extractor=Extractor()).plan(ClassificationRequest(question=q)).model_dump(mode='json')
 except ResearchError as e:result['error']=e.code
 result['elapsed_seconds']=time.monotonic()-start
Path('/app/audit/plan-a-english-diagnostic.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
