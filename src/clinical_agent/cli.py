"""CLI adapters; help is available before configuration and resource assembly."""

import argparse
import json
import logging
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, NoReturn
from uuid import UUID, uuid4

from pydantic import BaseModel, ValidationError

from clinical_agent.bootstrap import Runtime, open_runtime
from clinical_agent.command_runtime import (
    IngestionCommand,
    IngestionPort,
    ResearchPort,
    open_ingestion,
    open_research,
)
from clinical_agent.domain.analysis import AnalysisResult
from clinical_agent.domain.ingestion import BatchIngestionResult, ImportRequest
from clinical_agent.domain.openalex import OpenAlexOptions
from clinical_agent.domain.report import ReportResult
from clinical_agent.domain.research import QuestionRequest, ResearchAnswer, ResearchError
from clinical_agent.domain.retrieval import RetrievalError, RetrievalOptions

RuntimeFactory = Callable[[], AbstractContextManager[Runtime]]
IngestionFactory = Callable[[IngestionCommand], AbstractContextManager[IngestionPort]]
ResearchFactory = Callable[[Path], AbstractContextManager[ResearchPort]]


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(2, "Invalid arguments.\n")


def _error(request_id: UUID, code: str) -> None:
    print(json.dumps({"request_id": str(request_id), "error_code": code}), file=sys.stderr)


def _business(
    arguments: argparse.Namespace,
    runtime_factory: RuntimeFactory | None,
    ingestion_factory: IngestionFactory | None,
    research_factory: ResearchFactory | None,
) -> int:
    request_id = uuid4()
    try:
        if arguments.request_id is not None:
            request_id = UUID(arguments.request_id)
        if arguments.command == "ingest":
            request = ImportRequest(
                source_type=arguments.source_type,
                path=Path(arguments.path),
                allowed_root=Path(arguments.allowed_root),
                ingestion_time=datetime.now(UTC),
            )
            options = IngestionCommand(
                model_dir=Path(arguments.model_dir),
                snapshot_dir=Path(arguments.snapshot_dir),
                update_existing=arguments.update_existing,
            )
        else:
            if arguments.scope == "local" and (
                arguments.pubmed_query
                or arguments.openalex_query
                or arguments.date_from
                or arguments.date_to
            ):
                raise ValueError("PubMed filters require online scope")
            if (
                arguments.pubmed_query
                or arguments.date_field != "pdat"
                or arguments.sort != "relevance"
                or arguments.max_results != 10
            ):
                raise ValueError("PubMed-specific options retired; use OpenAlex")
            question = QuestionRequest(
                request_id=request_id,
                question=arguments.question,
                scope=arguments.scope,
                openalex=OpenAlexOptions(
                    query=arguments.openalex_query,
                    date_from=arguments.date_from,
                    date_to=arguments.date_to,
                )
                if arguments.scope != "local"
                else None,
                options=RetrievalOptions(
                    top_k=int(arguments.top_k),
                    min_similarity=float(arguments.min_similarity),
                    mode=arguments.retrieval_mode,
                    candidate_limit=arguments.candidate_limit,
                    keyword_query=arguments.keyword_query,
                    date_from=arguments.local_date_from,
                    date_to=arguments.local_date_to,
                ),
            )
    except (ValueError, TypeError):
        _error(request_id, "invalid_arguments")
        return 2
    executing = False
    try:
        runtime_context = (
            runtime_factory() if runtime_factory else open_runtime(request_id=request_id)
        )
        with runtime_context as runtime:
            if arguments.command == "ingest":
                factory = ingestion_factory or open_ingestion
                with factory(options) as service:
                    executing = True
                    result = BatchIngestionResult.model_validate(service.ingest(request))
                    payload = {
                        "request_id": str(request_id),
                        "result": result.model_dump(mode="json"),
                    }
                    code = (
                        0
                        if (
                            result.entries
                            and result.error_code is None
                            and all(
                                item.status
                                in {"imported", "already_present", "updated", "metadata_updated"}
                                for item in result.entries
                            )
                        )
                        else 3
                    )
            else:
                with (research_factory or open_research)(Path(arguments.model_dir)) as research:
                    executing = True
                    if arguments.report:
                        report_result = ReportResult.model_validate(research.report(question))
                        if report_result.report.request_id != request_id:
                            raise ValueError("Mismatched report correlation")
                        if arguments.format == "markdown":
                            print(report_result.markdown)
                            return 0
                        payload = report_result.model_dump(mode="json")
                        print(json.dumps(payload, ensure_ascii=True))
                        return 0
                    answer = (
                        AnalysisResult.model_validate(research.analyze(question))
                        if arguments.analyze
                        else ResearchAnswer.model_validate(research.answer(question))
                    )
                    if answer.request_id != request_id or (
                        isinstance(answer, ResearchAnswer)
                        and answer.retrieval_scope != question.scope
                    ):
                        raise ValueError("Mismatched answer correlation")
                    payload = answer.model_dump(mode="json")
                    code = 0
        # ASCII JSON preserves every Unicode code point on non-UTF8 Windows pipes too.
        rendered = json.dumps(payload, ensure_ascii=True)
        logging.getLogger("clinical_agent").info(
            "command_completed",
            extra={"request_id": str(request_id), "app_env": runtime.settings.app_env},
        )
        print(rendered)
        return code
    except KeyboardInterrupt:
        _error(request_id, "interrupted")
        return 130
    except Exception as error:
        exit_code = 1
        error_code = "command_failed"
        if isinstance(error, ValidationError) and not executing:
            error_code, exit_code = "invalid_configuration", 2
        elif isinstance(error, ModuleNotFoundError) and error.name in {
            "sqlalchemy",
            "psycopg",
            "pgvector",
            "sentence_transformers",
            "transformers",
            "torch",
            "langgraph",
            "langsmith",
            "httpx",
        }:
            error_code, exit_code = "missing_dependency", 2
        elif isinstance(error, (RetrievalError, ResearchError)):
            safe = (
                RetrievalError(error.code)
                if isinstance(error, RetrievalError)
                else ResearchError(error.code)
            )
            error_code = safe.code
        _error(request_id, error_code)
        return exit_code


# 软件环境诊断
class DoctorReport(BaseModel):
    status: Literal["ok"] = "ok"
    scope: Literal["local_environment"] = "local_environment"
    external_services_checked: Literal[False] = False
    python_version: str
    app_env: Literal["development", "test", "production"]
    request_id: UUID


def build_doctor_report(runtime: Runtime) -> DoctorReport:
    """Describe only the interpreter and the explicitly assembled configuration."""
    return DoctorReport(
        python_version=".".join(str(part) for part in sys.version_info[:3]),
        app_env=runtime.settings.app_env,
        request_id=runtime.request_id,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    runtime_factory: RuntimeFactory | None = None,
    ingestion_factory: IngestionFactory | None = None,
    research_factory: ResearchFactory | None = None,
) -> int:
    parser = _Parser(
        prog="clinical-agent",
        description="Clinical literature tooling: doctor, offline ingest and local RAG.",
        allow_abbrev=False,
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("doctor", help="Check the local environment without external services.")
    ingest = commands.add_parser(
        "ingest", help="Import one local PDF or PubMed XML file.", allow_abbrev=False
    )
    ingest.add_argument("--source-type", required=True, choices=["pdf", "pubmed_xml"])
    for flag in ("--path", "--allowed-root", "--snapshot-dir", "--model-dir"):
        ingest.add_argument(flag, required=True)
    ingest.add_argument("--request-id")
    ingest.add_argument(
        "--update-existing", action="store_true", help="Explicit atomic version update"
    )
    ask = commands.add_parser(
        "ask",
        help="Local RAG; sends retrieved excerpts to configured model API.",
        allow_abbrev=False,
    )
    output_mode = ask.add_mutually_exclusive_group()
    output_mode.add_argument("--report", action="store_true", help="Research topic report")
    ask.add_argument("--format", choices=["json", "markdown"], default="json")
    output_mode.add_argument(
        "--analyze", action="store_true", help="Phase 6 evidence analysis JSON"
    )
    ask.add_argument("--question", required=True)
    ask.add_argument("--retrieval-mode", choices=["vector", "keyword", "hybrid"], default="vector")
    ask.add_argument("--candidate-limit", type=int, default=50)
    ask.add_argument("--keyword-query")
    ask.add_argument("--local-date-from")
    ask.add_argument("--local-date-to")
    ask.add_argument("--scope", choices=["local", "online", "hybrid"], default="hybrid")
    ask.add_argument("--pubmed-query", help="retired; rejected")
    ask.add_argument("--openalex-query")
    ask.add_argument("--date-from")
    ask.add_argument("--date-to")
    ask.add_argument("--date-field", choices=["pdat", "edat"], default="pdat")
    ask.add_argument("--sort", choices=["relevance", "pub_date"], default="relevance")
    ask.add_argument("--max-results", type=int, default=10)
    ask.add_argument("--model-dir", required=True)
    ask.add_argument("--top-k", default="5")
    ask.add_argument("--min-similarity", default="0")
    ask.add_argument("--request-id")
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        parser.print_help()
        return 0
    if arguments.command != "doctor":
        return _business(arguments, runtime_factory, ingestion_factory, research_factory)

    entered = False  # 用于区分是否是配置初始化错误还是运行时错误
    try:
        factory = runtime_factory if runtime_factory is not None else open_runtime
        with factory() as runtime:
            entered = True
            report = build_doctor_report(runtime)
        logging.getLogger("clinical_agent").info(
            "local_check_completed",
            extra={"request_id": str(runtime.request_id), "app_env": runtime.settings.app_env},
        )
        print(report.model_dump_json())
    except Exception as exc:
        if isinstance(exc, ValidationError) and not entered:
            print("Invalid configuration.", file=sys.stderr)
            return 2
        if entered:
            logging.getLogger("clinical_agent").error(
                "local_check_failed",
                extra={
                    "request_id": str(runtime.request_id),
                    "app_env": runtime.settings.app_env,
                    "error_code": "local_check_failed",
                    "exception_type": type(exc).__name__,
                },
            )
        print("Local check failed.", file=sys.stderr)
        return 1
    return 0
