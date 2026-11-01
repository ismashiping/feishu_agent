"""Register the existing HTTP routes over explicitly injected runtime state."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from clinical_agent.api.execution import _SourceError, _State, execute
from clinical_agent.api.middleware import _error_response, identity
from clinical_agent.api.schemas import HealthReport, ImportBody, ImportResponse, QuestionBody
from clinical_agent.domain.analysis import AnalysisResult
from clinical_agent.domain.ingestion import BatchIngestionResult, ImportRequest
from clinical_agent.domain.report import ReportResult
from clinical_agent.domain.research import QuestionRequest, ResearchAnswer

if TYPE_CHECKING:
    from fastapi import FastAPI


def register_routes(app: "FastAPI", state: _State) -> None:
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.get("/health/live", response_model=HealthReport)
    async def live(request: Request) -> HealthReport:
        return HealthReport(request_id=identity(request), status="ok", scope="process")

    @app.get("/health/ready", response_model=HealthReport)
    async def ready(request: Request) -> HealthReport | JSONResponse:
        if not state.ready:
            return _error_response(request, "not_ready", 503, True)
        return HealthReport(request_id=identity(request), status="ok", scope="runtime")

    @app.post("/v1/questions", response_model=ResearchAnswer)
    async def question(body: QuestionBody, request: Request) -> ResearchAnswer | JSONResponse:
        def operation() -> ResearchAnswer:
            assert state.services is not None
            question = QuestionRequest(request_id=identity(request), **body.model_dump())
            answer = ResearchAnswer.model_validate(state.services.research.answer(question))
            if answer.request_id != question.request_id or answer.retrieval_scope != question.scope:
                raise ValueError("Answer correlation mismatch")
            return answer

        return await execute(state, request, operation)

    @app.post("/v1/reports", response_model=ReportResult)
    async def report(body: QuestionBody, request: Request) -> ReportResult | JSONResponse:
        def operation() -> ReportResult:
            assert state.services is not None
            question = QuestionRequest(request_id=identity(request), **body.model_dump())
            result = ReportResult.model_validate(state.services.research.report(question))
            if result.report.request_id != question.request_id:
                raise ValueError("Report correlation mismatch")
            return result

        return await execute(state, request, operation)

    @app.post("/v1/analyses", response_model=AnalysisResult)
    async def analysis(body: QuestionBody, request: Request) -> AnalysisResult | JSONResponse:
        def operation() -> AnalysisResult:
            assert state.services is not None
            question = QuestionRequest(request_id=identity(request), **body.model_dump())
            result = AnalysisResult.model_validate(state.services.research.analyze(question))
            if result.request_id != question.request_id:
                raise ValueError("Analysis correlation mismatch")
            return result

        return await execute(state, request, operation)

    @app.post("/v1/documents/import", response_model=ImportResponse)
    async def ingest(body: ImportBody, request: Request) -> ImportResponse | JSONResponse:
        def operation() -> ImportResponse:
            assert state.services is not None and state.settings is not None
            try:
                root = state.settings.import_root.resolve(strict=True)
                path = (root / body.relative_path).resolve(strict=True)
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError("Source outside import root")
            except (OSError, ValueError):
                raise _SourceError() from None
            incoming = ImportRequest(
                source_type=body.source_type,
                path=path,
                allowed_root=root,
                ingestion_time=datetime.now(UTC),
            )
            result = BatchIngestionResult.model_validate(state.services.ingestion.ingest(incoming))
            return ImportResponse(request_id=identity(request), result=result)

        return await execute(state, request, operation)
