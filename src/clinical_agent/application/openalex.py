"""Quality-driven discovery reusing the existing planner, evidence DTOs and chat model."""

import json
import logging
import re
import unicodedata
from datetime import UTC, date, datetime
from time import monotonic
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from clinical_agent.domain.models import EvidenceChunk, EvidenceLocation, SourceMetadata
from clinical_agent.domain.openalex import (
    AssessmentBatch,
    CandidateAssessment,
    OpenAlexError,
    OpenAlexOptions,
    OpenAlexProvenance,
    OpenAlexRecord,
    normalize_doi,
    parse_assessments,
    resolve_dates,
)
from clinical_agent.domain.pico import QueryPlan
from clinical_agent.domain.research import ResearchError
from clinical_agent.domain.retrieval import (
    DocumentSummary,
    EvidenceHit,
    RetrievalRequest,
    RetrievalResult,
)


class ScreeningPort(Protocol):
    def screen_candidates(self, context: dict[str, object], *, timeout_seconds: float) -> str: ...


ANALYSIS_FOCUS = {
    "bottlenecks",
    "challenges",
    "latest advances",
    "recent advances",
    "progress",
    "technical challenges",
    "technical bottlenecks",
    "limitations",
    "research gaps",
    "future directions",
    "open problems",
    "trends",
    "comparison",
    "differences",
}


_COUNT_KEY = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_TOKEN = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_REQUEST_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


_COUNT_WORD = frozenset({"unknown", "accepted", "rejected", "not_run"})
_MODEL_ID = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")
_FIELD_PATHS = re.compile(r"^[A-Za-z0-9_.,]{1,200}$")


def log_evidence_trace(
    *,
    stage: str,
    counts: dict[str, int | str],
    failure_kind: str = "",
    request_id: str | None = None,
    model_id: str | None = None,
    field_paths: str = "",
    rule_code: str = "",
    response_hash: str = "",
    finish_reason: str = "",
) -> None:
    """Log closed stage counts. Callers must not pass query text, titles, or secrets."""
    stage_text = (
        stage
        if stage in {"compile", "search", "screen", "select", "analyze", "fulltext", "provider"}
        else "unknown"
    )
    parts = []
    for key, value in counts.items():
        if not _COUNT_KEY.fullmatch(key):
            continue
        if type(value) is int and 0 <= value <= 1_000_000:
            parts.append(f"{key}={value}")
        elif value in _COUNT_WORD:
            parts.append(f"{key}={value}")
    count_text = ",".join(parts[:20])
    kind = failure_kind if _TOKEN.fullmatch(failure_kind) else ""
    extra = {"evidence_stage": stage_text, "evidence_counts": count_text}
    if kind:
        extra["failure_kind"] = kind
    if request_id and _REQUEST_ID.fullmatch(request_id):
        extra["request_id"] = request_id
    if model_id and _MODEL_ID.fullmatch(model_id):
        extra["model_id"] = model_id
    path_text = field_paths if field_paths and _FIELD_PATHS.fullmatch(field_paths) else ""
    rules = [item for item in rule_code.split(",") if _TOKEN.fullmatch(item)][:8]
    rule_text = ",".join(rules)
    digest = response_hash if re.fullmatch(r"[0-9a-f]{64}", response_hash) else ""
    finish = finish_reason if _TOKEN.fullmatch(finish_reason) else ""
    if path_text:
        extra["field_paths"] = path_text
    if rule_text:
        extra["rule_code"] = rule_text
    if digest:
        extra["response_hash"] = digest
    if finish:
        extra["finish_reason"] = finish
    tail = ""
    if rule_text:
        tail += f" rule_code={rule_text}"
    if path_text:
        tail += f" field_paths={path_text}"
    if digest:
        tail += f" response_hash={digest}"
    if finish:
        tail += f" finish_reason={finish}"
    logging.getLogger(__name__).info(
        f"Evidence trace stage={stage_text} failure_kind={kind} counts={count_text}{tail}",
        extra=extra,
    )


def method_names(plan: QueryPlan) -> list[str]:
    target = plan.paper_target
    if target is None or target.kind != "method":
        return []
    return list(
        dict.fromkeys(
            [
                target.source_text,
                *target.normalized_terms,
                *(
                    term
                    for mapping in plan.concept_mappings
                    if mapping.source_text == target.source_text and mapping.role == "method"
                    for term in mapping.english_terms
                ),
            ]
        )
    )


def paper_identity(plan: QueryPlan, hit: EvidenceHit, assessment: CandidateAssessment) -> str:
    """Metadata equality is distinct from source-supported method-origin judgment."""
    target = plan.paper_target
    if target is None:
        return "unresolved"
    if target.kind == "doi":
        doi = normalize_doi(hit.document.doi)
        if doi is None:
            return "unresolved"
        return "doi_match" if doi == normalize_doi(target.source_text) else "mismatch"
    if target.kind == "title":

        def normalized(text):
            return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", text).casefold())

        return (
            "title_match"
            if normalized(target.source_text) == normalized(hit.document.title)
            else "mismatch"
        )
    if assessment.study_role != "method_origin" or not assessment.origin_quote:
        return "unresolved"
    for name in method_names(plan):
        letters = re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", name).casefold())
        if not letters:
            continue
        # A name may vary in punctuation, but cannot be a suffix of another method.
        pattern = r"(?<![\w-])" + r"[\W_]*".join(map(re.escape, letters)) + r"(?![\w-])"
        if re.search(pattern, hit.document.title.casefold()) and re.search(
            pattern, assessment.origin_quote.casefold()
        ):
            return "method_origin_supported"
    return "unresolved"


def compile_queries(plan: QueryPlan) -> list[str]:
    """Only lexical expansion; required anchors survive in both strategies."""

    def literal(term):
        return '"' + term.replace('"', " ").replace("\\", " ") + '"'

    if plan.task_intent in {"paper_explanation", "definition"} and plan.paper_target:
        target = plan.paper_target
        if target.kind == "doi":
            query = literal(normalize_doi(target.source_text))
        elif target.kind == "title":
            query = literal(target.source_text)
        else:
            query = " OR ".join(literal(name) for name in method_names(plan))
        if len(query) > 4000:
            raise ResearchError("openalex_plan_required")
        return [query]

    if plan.concept_relations:
        constraints = plan.research_constraints
        content_quotes = (
            [
                *constraints.population,
                *constraints.task,
                *constraints.data_type,
                *constraints.paper_type,
            ]
            if constraints
            else []
        )
        keys = list(
            dict.fromkeys(
                r.concept_id
                for r in plan.concept_relations
                if r.required
                and (
                    r.english_term.casefold() not in ANALYSIS_FOCUS
                    or any(
                        q == r.source_text or q.casefold() == r.english_term.casefold()
                        for q in content_quotes
                    )
                )
                and (
                    not constraints.time_text
                    or constraints.time_text not in r.source_text
                    or any(q in r.source_text or r.source_text in q for q in content_quotes)
                )
            )
        )
        if not keys and plan.concept_groups:
            queries = [
                " AND ".join(
                    "(" + " OR ".join(literal(t) for t in g) + ")" for g in plan.concept_groups
                )
            ]
            comparison_groups = [
                "(" + " OR ".join(literal(t) for t in g) + ")" for g in plan.concept_groups
            ]
        else:
            queries = []
            for expand in [False, True]:
                groups = []
                for key in keys:
                    sources = {
                        r.source_text
                        for r in plan.concept_relations
                        if r.concept_id == key and r.required
                    }
                    terms = [
                        r.english_term
                        for r in plan.concept_relations
                        if r.concept_id == key
                        and (
                            r.required
                            or r.relation == "exact_synonym"
                            or expand
                            and r.relation in {"related_concept", "method"}
                        )
                    ]
                    # Same user phrase, standardized spelling. Not a new required concept.
                    for mapping in plan.concept_mappings:
                        if mapping.source_text in sources:
                            terms.extend(mapping.english_terms)
                    if plan.paper_target and plan.paper_target.source_text in sources:
                        terms.extend(plan.paper_target.normalized_terms)
                    known = {item.casefold() for item in [*terms, *sources]}
                    for group in plan.concept_groups:
                        if any(term.casefold() in known for term in group):
                            terms.extend(group)
                    terms = list(dict.fromkeys(terms))
                    groups.append("(" + " OR ".join(literal(t) for t in terms) + ")")
                joiner = (
                    " OR "
                    if plan.research_intent == "comparison"
                    and plan.task_intent != "feasibility"
                    and not constraints.population
                    else " AND "
                )
                queries.append(joiner.join(groups))
                if not expand:
                    comparison_groups = groups.copy()
    else:
        queries = [
            " AND ".join(
                "(" + " OR ".join(literal(t) for t in g) + ")" for g in plan.concept_groups
            )
        ]
        comparison_groups = [
            "(" + " OR ".join(literal(t) for t in g) + ")" for g in plan.concept_groups
        ]
    if plan.task_intent == "feasibility":
        base = queries[0]
        expanded = queries[-1]
        focused = [
            base,
            f'({expanded}) AND ("methods" OR "framework")',
            f'({expanded}) AND ("limitations" OR "challenges")',
        ]
        if not base or any(len(q) > 4000 for q in focused):
            raise ResearchError("openalex_plan_required")
        return focused
    if (
        plan.research_intent == "comparison"
        and not plan.research_constraints.population
        and len(comparison_groups) == 2
    ):
        queries = [queries[0], *comparison_groups]
    if not queries[0] or any(len(q) > 4000 for q in queries):
        raise ResearchError("openalex_plan_required")
    # A relaxed lexical expression retains the same required anchors; it changes
    # phrase matching without relaxing the actual screening/date constraints.
    if len(set(queries)) == 1:
        anchors = (
            list(
                dict.fromkeys(
                    r.english_term
                    for r in plan.concept_relations
                    if r.required and r.concept_id in keys
                )
            )
            if plan.concept_relations
            else [group[0] for group in plan.concept_groups]
        )
        relaxed = " ".join(anchors)
        if relaxed and len(relaxed) <= 4000:
            queries.append(relaxed)
    return list(dict.fromkeys(queries))


def record_hit(record: OpenAlexRecord, fetched_at: datetime) -> EvidenceHit:
    identity = uuid5(NAMESPACE_URL, record.openalex_id)
    metadata = SourceMetadata(
        source_type="openalex",
        source_url=record.openalex_id,
        source_uri=record.openalex_id,
        content_hash=record.content_hash,
        content_scope="abstract",
    )
    chunk = EvidenceChunk(
        chunk_id=uuid5(identity, record.content_hash),
        document_id=identity,
        text=record.abstract,
        location=EvidenceLocation(kind="abstract", start=0, end=len(record.abstract)),
        embedding_info=None,
        source_metadata=metadata,
    )
    document = DocumentSummary(
        **metadata.model_dump(),
        document_id=identity,
        title=record.title,
        title_origin="openalex_metadata",
        authors=record.authors,
        publication_date=record.publication_date,
        journal=record.journal,
        doi=record.doi,
        pmid=None,
        ingestion_time=fetched_at,
        openalex_record=record,
        publication_types=[record.work_type],
    )
    return EvidenceHit(
        chunk=chunk, document=document, score=1.0, score_type="openalex_rank", rank=1
    )


class OpenAlexRetrievalService:
    def __init__(
        self,
        searcher,
        screener: ScreeningPort,
        *,
        recent_months: int = 24,
        today=lambda: datetime.now(ZoneInfo("Asia/Shanghai")).date(),
        clock=monotonic,
    ):
        self.searcher, self.screener = searcher, screener
        self.recent_months, self.today, self.clock = recent_months, today, clock

    def retrieve(
        self,
        request: RetrievalRequest,
        *,
        query_plan: QueryPlan | None = None,
        timeout_seconds: float = 45.0,
        local: RetrievalResult | None = None,
        request_id: str | None = None,
    ) -> RetrievalResult:
        if request.pubmed is not None:
            raise ResearchError("openalex_options_retired")
        if query_plan is None or query_plan.research_constraints is None:
            raise ResearchError("openalex_plan_required")
        if query_plan.original_question != request.question:
            raise ResearchError("openalex_plan_required")
        constraints = query_plan.research_constraints
        options = request.openalex or OpenAlexOptions()
        try:
            start, end = resolve_dates(
                constraints,
                self.today(),
                recent_months=self.recent_months,
                explicit=(options.date_from, options.date_to),
            )
        except ValueError:
            raise ResearchError("openalex_invalid") from None
        queries = [options.query] if options.query else compile_queries(query_plan)
        deadline = self.clock() + min(45.0, timeout_seconds)
        network_deadline = min(deadline, self.clock() + 30.0)
        provenance = OpenAlexProvenance(
            query_sent=queries[0], fetched_at=datetime.now(UTC), date_from=start, date_to=end
        )
        pool, seen_dois, seen_pmids, seen_studies = {}, {}, {}, set()
        assessments = {}
        successful = 0
        identity_task = query_plan.task_intent in {"paper_explanation", "definition"}
        identity_queries = set()

        def usable(assessment):
            if identity_task:
                identity = paper_identity(query_plan, pool[assessment.id], assessment)
                provenance.identity_checks[assessment.id] = identity
                if identity in {"unresolved", "mismatch"}:
                    return False
            if not assessment.constraints_match:
                return False
            if assessment.relevance == "direct":
                return True
            # An original framework can support its side without being a
            # head-to-head study. Preserve its partial label and scope judgment.
            names = [t for group in query_plan.concept_groups for t in group]
            names += [r.english_term for r in query_plan.concept_relations if r.required]

            def normalized(text):
                return re.sub(r"\W+", "", text.casefold())

            return (
                query_plan.research_intent == "comparison"
                and assessment.study_role == "method_origin"
                and assessment.relevance == "partial"
                and any(
                    normalized(name) in normalized(dimension)
                    for name in names
                    for dimension in assessment.covered_dimensions
                )
            )

        def add(identity, hit):
            if identity in pool:
                return
            doi = normalize_doi(hit.document.doi)
            pmid = hit.document.pmid
            if (doi and doi in seen_dois) or (pmid and pmid in seen_pmids):
                provenance.candidate_outcomes[identity] = "duplicate_identity"
                return
            fingerprint = (
                re.sub(r"\W+", "", unicodedata.normalize("NFKC", hit.document.title).casefold()),
                " ".join(hit.chunk.text.casefold().split()),
            )
            # Different DOI versions must survive heuristic dedup when a precise
            # DOI was requested; otherwise an earlier version can hide the target.
            exact_doi = (
                identity_task
                and query_plan.paper_target is not None
                and query_plan.paper_target.kind == "doi"
            )
            if fingerprint in seen_studies and not exact_doi:
                provenance.candidate_outcomes[identity] = "duplicate_study"
                return
            seen_studies.add(fingerprint)
            if doi:
                seen_dois[doi] = identity
            if pmid:
                seen_pmids[pmid] = identity
            pool[identity] = hit

        if local:
            for hit in local.hits:
                add(str(hit.document.document_id), hit)

        for round_index in range(2):
            prior_round_ids = set(pool)
            query = queries[min(round_index, len(queries) - 1)]
            for sort_index, sort in enumerate(["relevance_score:desc", "publication_date:desc"]):
                purpose = "direct"
                if (
                    round_index == 1
                    and query_plan.task_intent == "feasibility"
                    and not options.query
                ):
                    query = queries[sort_index + 1]
                    sort = "relevance_score:desc"
                    purpose = ["technical_route", "bottlenecks"][sort_index]
                if identity_task:
                    sort, purpose = "relevance_score:desc", "paper_identity"
                    if query in identity_queries:
                        continue
                    identity_queries.add(query)
                if (
                    round_index == 1
                    and query_plan.task_intent != "feasibility"
                    and not options.query
                    and query_plan.research_intent == "comparison"
                    and len(queries) == 3
                ):
                    query, sort = queries[sort_index + 1], "relevance_score:desc"
                    purpose = "comparison_method"
                if self.clock() >= network_deadline or provenance.http_attempts >= 4:
                    provenance.status = "partial"
                    provenance.warnings.append("openalex_budget")
                    break
                provenance.http_attempts += 1
                trace = {
                    "round": round_index + 1,
                    "purpose": purpose,
                    "query": query,
                    "sort": sort,
                    "date_from": str(start) if start else None,
                    "date_to": str(end) if end else None,
                }
                try:
                    records, count, warnings = self.searcher.search(
                        query,
                        date_from=start,
                        date_to=end,
                        sort=sort,
                        timeout_seconds=network_deadline - self.clock(),
                    )
                    successful += 1
                    trace.update(status="complete", returned_ids=[r.openalex_id for r in records])
                    provenance.total_count = max(provenance.total_count, count)
                    provenance.truncated |= count > len(records)
                    provenance.warnings.extend(warnings)
                    for record in records:
                        if (
                            record.openalex_id not in {r.openalex_id for r in provenance.records}
                            and len(provenance.records) < 40
                        ):
                            provenance.records.append(record)
                        if record.openalex_id in pool:
                            continue
                        if len(pool) >= 40:
                            provenance.candidate_outcomes[record.openalex_id] = "candidate_budget"
                        elif record.abstract_status != "available":
                            provenance.candidate_outcomes[record.openalex_id] = (
                                record.abstract_status
                            )
                        elif record.is_retracted:
                            provenance.candidate_outcomes[record.openalex_id] = "retracted"
                        else:
                            add(record.openalex_id, record_hit(record, provenance.fetched_at))
                except OpenAlexError as error:
                    trace.update(status="failed", error=error.code)
                    provenance.status = "partial"
                    provenance.warnings.append(error.code)
                provenance.query_rounds.append(trace)

            pending = {}
            # Supplemental papers must not stay behind previously unscreened
            # leftovers and disappear again at the same input budget boundary.
            for identity, hit in sorted(pool.items(), key=lambda item: item[0] in prior_round_ids):
                if identity in assessments:
                    continue
                publication = hit.document.publication_date
                if start and (
                    publication.precision != "day"
                    or not start
                    <= date(publication.year, publication.month, publication.day)
                    <= end
                ):
                    provenance.candidate_outcomes[identity] = "date_mismatch_or_unknown"
                    continue
                if (
                    hit.document.source_type not in request.options.source_types
                    or hit.document.content_scope not in request.options.content_scopes
                ):
                    provenance.candidate_outcomes[identity] = "source_policy"
                    continue
                pending[identity] = {
                    "id": identity,
                    "title": hit.document.title,
                    "doi": hit.document.doi,
                    "abstract": hit.chunk.text,
                    "publication_date": publication.model_dump(mode="json"),
                    "paper_types": hit.document.publication_types,
                }
            context = {
                "question": request.question,
                "task_intent": query_plan.task_intent,
                "paper_target": query_plan.paper_target.model_dump()
                if query_plan.paper_target
                else None,
                "constraints": constraints.model_dump(mode="json"),
                "output_schema": AssessmentBatch.model_json_schema(),
                "candidates": [],
            }
            context["output_schema"]["$defs"]["CandidateAssessment"]["properties"][
                "covered_dimensions"
            ]["items"]["enum"] = constraints.answer_dimensions
            for identity, item in pending.items():
                context["candidates"].append(item)
                if len(json.dumps(context, ensure_ascii=False).encode()) > 24000:
                    context["candidates"].pop()
                    provenance.candidate_outcomes[identity] = "screening_input_budget"
            supplied = {
                item["id"]: (item["title"], item["abstract"]) for item in context["candidates"]
            }
            if supplied and self.clock() < deadline:
                provenance.screening_calls += 1
                try:
                    raw = self.screener.screen_candidates(
                        context, timeout_seconds=deadline - self.clock()
                    )
                    if self.clock() >= deadline:
                        raise TimeoutError("Screening deadline")
                    if len(raw.encode()) > 16000:
                        raise ValueError("Screening output budget")
                    data = json.loads(raw)
                    if not isinstance(data, dict) or set(data) != {"assessments"}:
                        raise ValueError("Unexpected screening envelope")
                    if not isinstance(data["assessments"], list) or any(
                        not isinstance(a, dict) or not isinstance(a.get("id"), str)
                        for a in data["assessments"]
                    ):
                        raise ValueError("Invalid screening identities")
                    ids = [a["id"] for a in data["assessments"]]
                    if len(set(ids)) != len(ids) or set(ids) != set(supplied):
                        raise ValueError("Screening candidate identity mismatch")
                    for item in data["assessments"]:
                        identity = item["id"]
                        try:
                            assessment = parse_assessments(
                                json.dumps({"assessments": [item]}),
                                {identity: supplied[identity]},
                            )[0]
                            if not set(assessment.covered_dimensions) <= set(
                                constraints.answer_dimensions
                            ):
                                raise ValueError("Unrequested dimension")
                            assessments[identity] = assessment
                        except ValueError:
                            provenance.status = "partial"
                            provenance.warnings.append("openalex_assessment_invalid")
                            provenance.candidate_outcomes[identity] = "screening_failed"
                except (ResearchError, ValueError, TimeoutError) as error:
                    provenance.status = "partial"
                    provenance.warnings.append("openalex_screening_failed")
                    failure_kind = (
                        error.code
                        if isinstance(error, ResearchError)
                        else "timeout"
                        if isinstance(error, TimeoutError)
                        else "screening_invalid"
                    )
                    log_evidence_trace(
                        stage="screen",
                        counts={"supplied": len(supplied)},
                        failure_kind=failure_kind,
                        request_id=request_id,
                    )
                    for identity in supplied:
                        provenance.candidate_outcomes[identity] = "screening_failed"
            direct = [a for a in assessments.values() if usable(a)]
            covered = {d for a in direct for d in a.covered_dimensions}
            gaps = sorted(set(constraints.answer_dimensions) - covered)
            provenance.evidence_gaps = (["no_direct_evidence"] if not direct else []) + gaps
            if identity_task and not direct:
                provenance.evidence_gaps.append("paper_identity_unresolved")
            # Soft coverage target only triggers bounded supplemental search.
            # A sparse field remains sparse; eligibility never changes to fill it.
            if (
                len(direct) >= min(5, request.options.top_k)
                and not gaps
                and (
                    query_plan.research_intent != "comparison"
                    and query_plan.task_intent != "feasibility"
                    or round_index == 1
                )
            ):
                break
            if self.clock() >= deadline:
                provenance.status = "partial"
                break

        if not successful:
            code = next(
                (w for w in provenance.warnings if w != "openalex_budget"), "openalex_timeout"
            )
            raise ResearchError(code)
        provenance.assessments = list(assessments.values())
        if direct and len(direct) < min(5, request.options.top_k):
            provenance.evidence_gaps.append("limited_independent_evidence")
        eligible = []
        for identity, hit in pool.items():
            assessment = assessments.get(identity)
            if assessment:
                provenance.candidate_outcomes[identity] = assessment.relevance
                if usable(assessment):
                    eligible.append((identity, hit, assessment))
            elif identity not in provenance.candidate_outcomes:
                provenance.candidate_outcomes[identity] = "not_screened"

        def quality(item):
            _, hit, assessment = item
            r = hit.document.openalex_record
            return (
                not assessment.experimental_information,
                not assessment.representative,
                not bool(r and r.best_oa_location),
                -(hit.document.publication_date.year or 0),
                item[0],
            )

        # Cover evidenced question dimensions before filling remaining quality slots.
        selected, covered = [], set()
        remaining = sorted(eligible, key=quality)
        while remaining and len(selected) < request.options.top_k:
            item = min(
                remaining,
                key=lambda x: (
                    query_plan.research_intent == "comparison"
                    and x[2].study_role != "method_origin",
                    -len(set(x[2].covered_dimensions) - covered),
                    quality(x),
                ),
            )
            remaining.remove(item)
            selected.append(item)
            covered.update(item[2].covered_dimensions)
        hits = []
        online_rank = 0
        for identity, hit, _ in selected:
            provenance.candidate_outcomes[identity] = "selected"
            if hit.score_type == "openalex_rank":
                online_rank += 1
                hit = hit.model_copy(update={"score": 1.0 / online_rank})
            hits.append(hit)
        hits.sort(
            key=lambda h: (
                1 if h.score_type == "openalex_rank" else 0,
                -h.score,
                h.chunk.chunk_id.int,
            )
        )
        provenance.returned_count = len(pool)
        outcomes = list(provenance.candidate_outcomes.values())
        returned = sum(len(item.get("returned_ids") or []) for item in provenance.query_rounds)
        log_evidence_trace(
            stage="select",
            counts={
                "http": provenance.http_attempts,
                "returned": returned,
                "records": len(provenance.records),
                "screened": len(assessments),
                "screening_failed": outcomes.count("screening_failed"),
                "screening_budget": outcomes.count("screening_input_budget"),
                "eligible": len(eligible),
                "hits": len(hits),
            },
            failure_kind="" if hits else "no_direct_evidence",
            request_id=request_id,
        )
        return RetrievalResult(
            scope="hybrid" if local else "online",
            options=request.options,
            embedding_info=local.embedding_info if local else None,
            channel_status=local.channel_status
            if local
            else {"keyword": "not_requested", "vector": "ok"},
            strategy_version=local.strategy_version if local else "vector-v1",
            hits=[h.model_copy(update={"rank": i}) for i, h in enumerate(hits, 1)],
            search_provenance=provenance,
            warnings=list(dict.fromkeys(provenance.warnings)),
        )
