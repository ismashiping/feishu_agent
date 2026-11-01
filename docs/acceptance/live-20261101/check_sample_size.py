import json,os,time
from pathlib import Path
from dotenv import dotenv_values
from clinical_agent.integrations.llm import LLMSettings,open_llm
from clinical_agent.application.analysis import EvidenceAnalyzer
from clinical_agent.application.report import ReportBuilder
from clinical_agent.integrations.report_snapshot import SnapshotVerifier
from clinical_agent.domain.research import QuestionRequest
from clinical_agent.domain.retrieval import RetrievalResult
from clinical_agent.domain.pico import QueryPlan
from clinical_agent.domain.report import render_report
for k,v in dotenv_values('.artifacts/docker-e2e/compose.env').items():
    if v is not None:os.environ[k]=v
root=Path('docs/acceptance/sample-size-20261102');root.mkdir(exist_ok=False)
old=Path('docs/acceptance/live-report-context-restored-20261102')
retrieval=RetrievalResult.model_validate_json((old/'repeat-fulltext_rag.json').read_text(encoding='utf8'))
plan=QueryPlan.model_validate_json((old/'repeat-plan.json').read_text(encoding='utf8'))
request=QuestionRequest(request_id=__import__('uuid').uuid4(),question=plan.original_question,scope=retrieval.scope,options=retrieval.options)
with open_llm(LLMSettings()) as model:
    original=model.analyze_evidence
    def capture(context,**kwargs):
        raw=original(context,**kwargs)
        (root/'raw-selection.json').write_text(raw,encoding='utf8')
        return raw
    model.analyze_evidence=capture
    start=time.monotonic()
    analysis=EvidenceAnalyzer(model=model).analyze(request,retrieval,query_plan=plan)
    analysis_seconds=time.monotonic()-start
    (root/'analysis.json').write_text(analysis.model_dump_json(indent=2),encoding='utf8')
    start=time.monotonic()
    report=ReportBuilder(reviewer=model,snapshots=SnapshotVerifier()).build(request,analysis,retrieval)
    (root/'report.json').write_text(report.model_dump_json(indent=2),encoding='utf8')
    (root/'report.md').write_text(render_report(report),encoding='utf8')
    result={'analysis_seconds':analysis_seconds,'review_seconds':time.monotonic()-start,'sample_size':[s.fields['sample_size'].model_dump(mode='json') for s in analysis.studies],'status':report.status,'unsupported':[c.model_dump(mode='json') for c in report.claims if c.support_status=='unsupported']}
    (root/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))
