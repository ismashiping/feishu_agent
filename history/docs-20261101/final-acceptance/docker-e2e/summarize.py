import json
from pathlib import Path
p=Path('docs/final-acceptance/docker-e2e')
summary={}
for lang in ['zh','en']:
 f=p/('actual-'+lang+'.json')
 if not f.exists():continue
 d=json.loads(f.read_text(encoding='utf-8'));s=d.get('search',{});a=d.get('answer',{})
 summary[lang]={'error':d.get('error'),'query':s.get('query_sent'),'translation':s.get('query_translation'),'total':s.get('total_count'),'pmids':s.get('searched_pmids'),'truncated':s.get('truncated'),'llm_attempts':d.get('llm_attempts',0),'usage':d.get('usage',[]),'pubmed_http_attempts':d.get('pubmed_http_attempts',0),'context_characters':d.get('context_characters'),'claims':a.get('claims'),'sources':[{k:r.get(k) for k in ['pmid','title']} for r in a.get('sources',[])],'limitations':a.get('limitations'),'elapsed_seconds':d.get('elapsed_seconds')}
(p/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
