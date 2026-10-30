import json,time,traceback
from pathlib import Path
from uuid import uuid4
from clinical_agent.command_runtime import open_research
from clinical_agent.domain.research import QuestionRequest
out=Path('/app/audit')
questions=[('zh','有没有关于肝脏肿瘤内部亚区划分的研究？有哪些代表性论文，采用了什么亚区划分方法？'),('en','Are there studies on intratumoral subregion delineation in liver tumors? What representative papers exist, and what methods do they use to define these subregions?')]
def save(name,obj): (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
try:
 with open_research(Path('/app/model')) as service:
  gen=service._generator; model=gen._model; current={}
  class ModelRecorder:
   def invoke(self,*a,**kw):
    current['llm_attempts']=current.get('llm_attempts',0)+1
    msg=model.invoke(*a,**kw)
    current.setdefault('usage',[]).append(msg.usage_metadata)
    return msg
  gen._model=ModelRecorder()
  orig_plan=service._planner.plan
  def plan(*a,**kw):
   p=orig_plan(*a,**kw);current['plan']=p.model_dump(mode='json');return p
  service._planner.plan=plan
  searcher=service._online_retriever._searcher; orig_search=searcher.search; orig_req=searcher._request
  original_stream=searcher._client.stream
  def stream(*a,**kw):
   current['pubmed_http_attempts']=current.get('pubmed_http_attempts',0)+1
   return original_stream(*a,**kw)
  searcher._client.stream=stream
  def req(endpoint,*a,**kw):
   current.setdefault('pubmed_endpoints',[]).append(endpoint)
   return orig_req(endpoint,*a,**kw)
  searcher._request=req
  def search(*a,**kw):
   r=orig_search(*a,**kw);current['search']=r.model_dump(mode='json');return r
  searcher.search=search
  original_generate=gen.generate
  def generate(context,**kw):
   current['context_characters']=len(context.model_dump_json());current['context']=context.model_dump(mode='json')
   return original_generate(context,**kw)
  gen.generate=generate
  for label,q in questions:
   current={};start=time.monotonic()
   try:current['answer']=service.answer(QuestionRequest(question=q,scope='online',request_id=uuid4())).model_dump(mode='json')
   except Exception as e:current['error']=getattr(e,'code',type(e).__name__)
   current['elapsed_seconds']=time.monotonic()-start;save('actual-'+label+'.json',current)
except Exception as e:
 save('runtime-failure.json',{'type':type(e).__name__,'code':getattr(e,'code',None),'dependency':getattr(e,'name',None),'frames':traceback.format_tb(e.__traceback__)})
