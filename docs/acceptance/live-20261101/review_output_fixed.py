import json,os,time
from pathlib import Path
from dotenv import dotenv_values
from clinical_agent.integrations.llm import LLMSettings,open_llm
from clinical_agent.application.report import ReportBuilder
from clinical_agent.integrations.report_snapshot import SnapshotVerifier
from clinical_agent.domain.analysis import AnalysisResult
from clinical_agent.domain.research import QuestionRequest
from clinical_agent.domain.retrieval import RetrievalResult
from clinical_agent.domain.report import render_report
for k,v in dotenv_values('.artifacts/docker-e2e/compose.env').items():
    if v is not None:os.environ[k]=v
root=Path('docs/acceptance/review-output-budget-fixed-20261102');root.mkdir(exist_ok=False)
old=Path('docs/acceptance/final-live-20261102')
summary=[]
with open_llm(LLMSettings()) as model:
    original=model.review_claims
    for run in ['first','repeat']:
        batches=[]
        def review(context,**kwargs):
            start=time.monotonic()
            raw=original(context,**kwargs)
            batches.append({'context':context,'raw_response':raw,'seconds':time.monotonic()-start})
            (root/f'{run}-batches.json').write_text(json.dumps(batches,ensure_ascii=False,indent=2),encoding='utf8')
            return raw
        model.review_claims=review
        baseline=json.loads((old/f'{run}-report.json').read_text(encoding='utf8'))['report']
        analysis=AnalysisResult.model_validate(baseline['analysis'])
        retrieval=RetrievalResult.model_validate_json((old/f'{run}-fulltext_rag.json').read_text(encoding='utf8'))
        request=QuestionRequest(request_id=analysis.request_id,question=analysis.original_idea,scope=retrieval.scope,options=retrieval.options)
        start=time.monotonic()
        report=ReportBuilder(reviewer=model,snapshots=SnapshotVerifier()).build(request,analysis,retrieval)
        (root/f'{run}-report.json').write_text(report.model_dump_json(indent=2),encoding='utf8')
        (root/f'{run}-report.md').write_text(render_report(report),encoding='utf8')
        compared=[]
        for before,after in zip(baseline['claims'],report.claims,strict=True):
            assert before['text']==after.text and before['claim_id']==after.claim_id
            if True:
                compared.append({'claim_id':after.claim_id,'text':after.text,'before':before['support_status'],'after':after.support_status,'before_basis':before['basis'],'after_basis':after.basis})
        summary.append({'run':run,'seconds':time.monotonic()-start,'batches':len(batches),'status':report.status,'notes':report.verification_notes,'comparisons':compared})
        (root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(summary[-1],ensure_ascii=False),flush=True)
