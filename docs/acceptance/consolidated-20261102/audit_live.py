"""Read-only independent audit of consolidated live artifacts."""
import json
from collections import Counter
from pathlib import Path
root=Path('docs/acceptance/consolidated-20261102/live')
state=json.loads((root/'events.json').read_text(encoding='utf8'))
audit=[]
for result in state['results']:
 run=result['run']
 row={'run':run,'entry_result':result}
 if result['status']!='returned':
  audit.append(row);continue
 report=json.loads((root/f'{run}-report.json').read_text(encoding='utf8'))['report']
 events=[e for e in state['events'] if e['run']==run]
 groups=[];current=[]
 for e in events:
  if e['stage']=='review_batch':current.append(e)
  if e['stage']=='report_review':groups.append(current);current=[]
 batches=groups[-1] if groups else []
 ids=[]
 for batch in batches:
  assert len(batch['claim_ids'])<=6 and batch['context_characters']<=32000
  ids.extend(batch['claim_ids'])
 successful=[e for e in batches if e['status']=='ok']
 claims=report['claims']
 chunks={e['chunk_id']:e for s in report['analysis']['sources'] for e in s['evidence']}
 pointers=[p for c in claims for p in c['evidence']]
 quote_ok=all(p['chunk_id'] in chunks and p['quote'] in chunks[p['chunk_id']]['text'] for p in pointers)
 coverage=(len(ids)==len(set(ids))==len(claims) and set(ids)=={c['claim_id'] for c in claims} and len(successful)==len(batches) and all(c['basis']!='not_reviewed' for c in claims))
 row.update(claims=len(claims),papers=len(report['analysis']['sources']),passages=len(chunks),review_batches=len(batches),review_complete=coverage,quote_checks=len(pointers),quotes_match=quote_ok,only_fulltext=all(e['location']['kind']=='fulltext' for e in chunks.values()),support=dict(Counter(c['support_status'] for c in claims)),feedback_stop=report['feedback_stop'],notes=report['verification_notes'],cache_hits=[e['paper_key'] for e in events if e['stage']=='cache_load' and e.get('hit')],feasibility=[(x['dimension'],x['status']) for x in report['analysis']['feasibility']],sample_sizes=[s['fields']['sample_size'].model_dump() if hasattr(s['fields']['sample_size'],'model_dump') else s['fields']['sample_size'] for s in report['analysis']['studies']])
 audit.append(row)
Path('docs/acceptance/consolidated-20261102/audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
for row in audit:print(json.dumps({k:v for k,v in row.items() if k not in ['sample_sizes','notes']},ensure_ascii=False))
