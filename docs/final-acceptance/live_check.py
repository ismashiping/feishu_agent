import json
from pathlib import Path
from uuid import uuid4
from time import monotonic
from dotenv import dotenv_values
from clinical_agent.adapters.llm import LLMSettings, open_llm
from clinical_agent.adapters.pubmed_online import open_pubmed
from clinical_agent.application.pico import PicoPlanner
from clinical_agent.application.pubmed import PubMedRetrievalService
from clinical_agent.application.research import ResearchService
from clinical_agent.domain.research import QuestionRequest
out=Path('docs/final-acceptance')
def save(name,obj): (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
values=dotenv_values('.env')
try:
    settings=LLMSettings(**{k:values['LLM_'+k.upper()] for k in LLMSettings.model_fields if values.get('LLM_'+k.upper())})
except Exception:
    save('live.json',{'status':'not_executed','reason':'LLM settings unavailable or invalid; no secrets logged'})
    settings=None
questions=['有没有关于肝脏肿瘤内部亚区划分的研究？有哪些代表性论文，采用了什么亚区划分方法？','Are there studies on intratumoral subregion delineation in liver tumors? What representative papers exist, and what methods do they use to define these subregions?']
with open_pubmed() as pubmed:
    if settings:
      with open_llm(settings) as gen:
        for label,q in zip(['zh','en'],questions):
          audit={}
          class Search:
            def search(self,request,**kw):
              audit['plan']=request.query_plan.model_dump(mode='json')
              audit['query']=request.query_text()
              result=pubmed.search(request,**kw)
              audit['search']=result.model_dump(mode='json')
              return result
          class Generator:
            def generate(self,context,**kw):
              audit['context_characters']=len(context.model_dump_json())
              audit['evidence_characters']=sum(len(e.text) for e in context.evidence)
              audit['context']=context.model_dump(mode='json')
              return gen.generate(context,**kw)
          service=ResearchService(retriever=object(),generator=Generator(),planner=PicoPlanner(extractor=gen),online_retriever=PubMedRetrievalService(Search()))
          start=monotonic()
          try: audit['answer']=service.answer(QuestionRequest(question=q,scope='online',request_id=uuid4())).model_dump(mode='json')
          except Exception as e: audit['error']=getattr(e,'code',type(e).__name__)
          audit['elapsed_seconds']=monotonic()-start
          save(label+'.json',audit)
    try: save('independent-pmids.json',[r.model_dump(mode='json') for r in pubmed.fetch_metadata(['39752907','40601290','41058349'])])
    except Exception as e: save('independent-pmids.json',{'error':getattr(e,'code',type(e).__name__)})
