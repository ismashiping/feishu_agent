"""Bounded real threads and shared RAG, with explicit Redis/delivery substitutes."""

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import UTC, datetime
from threading import Barrier, Event, Lock
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from pydantic import ValidationError

from clinical_agent.domain.citations import build_answer
from clinical_agent.domain.research import QuestionRequest
from clinical_agent.domain.retrieval import RetrievalResult, retrieval_embedding_info
from feishu.dedup import AcquireResult, DedupPolicy, Lease
from feishu.events import MessageEnvelope
from tests.unit.test_evidence_analysis import case as case


def envelope(index=1):
    identity = ("app", "message", f"om_{index}")
    return MessageEnvelope(
        app_id="app",
        message_id=identity[2],
        sender_id="ou_user",
        chat_id="oc_chat",
        chat_type="p2p",
        text="Synthetic question?",
        request_id=uuid5(NAMESPACE_URL, json.dumps(identity, separators=(",", ":"))),
    )


def answer(request):
    result = RetrievalResult(
        options=request.options, embedding_info=retrieval_embedding_info(), hits=[]
    )
    if request.scope == "hybrid":
        from clinical_agent.application.pubmed import merge_sources

        result = merge_sources(result, EmptyOnline().retrieve(request))
    return build_answer(request, result, None, generated_at=datetime(2026, 10, 27, tzinfo=UTC))


class EmptyOnline:
    """Explicit no-network online channel for worker/real-graph contract tests."""

    def retrieve(self, request, **kwargs):
        from clinical_agent.domain.pubmed import SearchProvenance

        return RetrievalResult(
            scope="online",
            options=request.options,
            embedding_info=None,
            hits=[],
            search_provenance=SearchProvenance(
                query_sent=request.question,
                query_translation=None,
                total_count=0,
                requested_limit=10,
                returned_count=0,
                truncated=False,
                fetched_at=datetime(2026, 10, 27, tzinfo=UTC),
                date_from=None,
                date_to=None,
                date_field="pdat",
                sort="relevance",
                status="complete",
                warnings=[],
                missing_pmids=[],
            ),
        )


class Dedup:
    policy = DedupPolicy(lease_ms=120000)

    def __init__(self):
        self.calls = []
        self.owners = {}
        self.lock = Lock()
        self.acquisition = "acquired"
        self.checks = []

    def acquire(self, identity):
        with self.lock:
            self.calls.append(("acquire", identity))
            if self.acquisition != "acquired":
                return AcquireResult(self.acquisition)
            if identity in self.owners:
                return AcquireResult("duplicate")
            lease = Lease(identity=identity, owner=uuid4())
            self.owners[identity] = lease
            return AcquireResult("acquired", lease)

    def check(self, lease):
        self.calls.append(("check", lease))
        return self.checks.pop(0) if self.checks else "owned"

    def release(self, lease):
        self.calls.append(("release", lease))
        if self.owners.get(lease.identity) == lease:
            del self.owners[lease.identity]
        return "owned"


class Service:
    def respond(self, request):
        return self.answer(request)

    def __init__(self):
        self.requests = []
        self.entered, self.finish = Event(), Event()
        self.finish.set()
        self.error = False

    def answer(self, request):
        self.requests.append(request)
        self.entered.set()
        assert self.finish.wait(5)
        if self.error:
            raise RuntimeError("private-secret-question")
        return answer(request)


class Sink:
    def __init__(self):
        self.deliveries = []
        self.accept = True
        self.error = False

    def offer(self, delivery):
        self.deliveries.append(delivery)
        if self.error:
            raise RuntimeError("private-secret-token")
        return self.accept


@pytest.fixture
def setup_worker():
    from feishu.worker import Dispatcher, WorkerPolicy

    service, dedup, sink = Service(), Dedup(), Sink()
    worker = Dispatcher(research=service, dedup=dedup, sink=sink, policy=WorkerPolicy(capacity=1))
    try:
        yield worker, service, dedup, sink
    finally:
        service.finish.set()
        assert worker.close(timeout_seconds=5)


def test_handoff_preserves_dto_identity_and_lease(setup_worker):
    worker, service, dedup, sink = setup_worker
    message = envelope()
    submission = worker.submit(message)
    assert submission.status == "accepted"
    assert submission.future.result(3).status == "queued"
    delivery = sink.deliveries[0]
    assert delivery.envelope == message and delivery.answer == answer(service.requests[0])
    assert delivery.answer.request_id == message.request_id and delivery.error_code is None
    assert delivery.lease == dedup.owners[message.dedup_identity]
    assert [x[0] for x in dedup.calls] == ["acquire", "check", "check"]


def test_busy_timeout_cancel_hold_capacity_until_real_completion(setup_worker):
    worker, service, dedup, _ = setup_worker
    service.finish.clear()
    first = worker.submit(envelope())
    assert service.entered.wait(3)
    with pytest.raises(TimeoutError):
        first.future.result(0.001)
    assert first.future.cancel() is False
    assert worker.submit(envelope(2)).status == "busy"
    assert sum(x[0] == "acquire" for x in dedup.calls) == 1
    service.finish.set()
    assert first.future.result(3).status == "queued"
    assert worker.submit(envelope(2)).future.result(3).status == "queued"


@pytest.mark.parametrize("status", ["duplicate", "unavailable"])
def test_acquire_rejection_restores_capacity(setup_worker, status):
    worker, service, dedup, sink = setup_worker
    dedup.acquisition = status
    result = worker.submit(envelope())
    assert result.status == status and result.future is None
    assert not service.requests and not sink.deliveries
    dedup.acquisition = "acquired"
    assert worker.submit(envelope()).future.result(3).status == "queued"


@pytest.mark.parametrize(
    "checks", [["lost"], ["unavailable"], ["owned", "lost"], ["owned", "unavailable"]]
)
def test_owner_checks_stop_research_or_handoff(setup_worker, checks):
    worker, service, dedup, sink = setup_worker
    dedup.checks = list(checks)
    assert worker.submit(envelope()).future.result(3).status == checks[-1]
    assert len(service.requests) == len(checks) - 1
    assert not sink.deliveries and not any(x[0] == "release" for x in dedup.calls)


@pytest.mark.parametrize("error", [False, True])
def test_sink_full_releases_but_unknown_preserves_lease(setup_worker, error):
    worker, _, dedup, sink = setup_worker
    sink.accept, sink.error = False, error
    result = worker.submit(envelope()).future.result(3)
    assert result.status == ("delivery_unknown" if error else "delivery_failed")
    assert bool(dedup.owners) is error
    assert "private" not in repr(result)


@pytest.mark.parametrize("invalid", ["raises", "bad_dto", "wrong_request"])
def test_research_failure_is_fixed_delivery_error(setup_worker, invalid):
    worker, service, _, sink = setup_worker
    if invalid == "raises":
        service.error = True
    elif invalid == "bad_dto":
        service.answer = lambda _: {"private": "secret"}
    else:
        service.answer = lambda _: answer(QuestionRequest(question="other", request_id=uuid4()))
    assert worker.submit(envelope()).future.result(3).status == "queued"
    delivery = sink.deliveries[0]
    assert delivery.answer is None and delivery.error_code == "research_failed"


def test_late_result_is_discarded_without_releasing_running_capacity(setup_worker):
    worker, service, dedup, sink = setup_worker
    now = [0.0]
    worker._clock = lambda: now[0]
    service.finish.clear()
    task = worker.submit(envelope())
    assert service.entered.wait(3)
    now[0] = 91.0
    assert worker.submit(envelope(2)).status == "busy"
    service.finish.set()
    assert task.future.result(3).status == "timed_out"
    assert not sink.deliveries and not dedup.owners


def test_close_deadline_stops_admission_but_does_not_close_borrowed_resources(setup_worker):
    worker, service, dedup, _ = setup_worker
    service.finish.clear()
    task = worker.submit(envelope())
    assert service.entered.wait(3)
    assert worker.close(timeout_seconds=0.001) is False
    assert worker.submit(envelope(2)).status == "closed"
    service.finish.set()
    assert task.future.result(3).status == "queued"
    assert worker.close(timeout_seconds=3) is True
    assert dedup.owners


def test_submit_failure_cleans_owned_resources(setup_worker, monkeypatch):
    worker, _, dedup, _ = setup_worker
    original = worker._executor.submit

    def fail(*args):
        raise RuntimeError("private-secret")

    monkeypatch.setattr(worker._executor, "submit", fail)
    assert worker.submit(envelope()).status == "submit_failed"
    assert not dedup.owners
    monkeypatch.setattr(worker._executor, "submit", original)
    assert worker.submit(envelope()).future.result(3).status == "queued"


def test_concurrent_duplicates_call_one_shared_service():
    from feishu.worker import Dispatcher, WorkerPolicy

    service, dedup, sink = Service(), Dedup(), Sink()
    service.finish.clear()
    worker = Dispatcher(research=service, dedup=dedup, sink=sink, policy=WorkerPolicy(capacity=4))
    barrier = Barrier(4)

    def submit():
        barrier.wait(3)
        return worker.submit(envelope())

    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: submit(), range(4)))
        assert [r.status for r in results].count("accepted") == 1
        assert [r.status for r in results].count("duplicate") == 3
        assert service.entered.wait(3) and len(service.requests) == 1
    finally:
        service.finish.set()
        assert worker.close(timeout_seconds=5)


@pytest.mark.parametrize(
    "values",
    [
        {"capacity": 0},
        {"capacity": 5},
        {"capacity": True},
        {"capacity": "2"},
        {"processing_ms": 0},
        {"processing_ms": 240001},
        {"handoff_ms": True},
        {"handoff_ms": 30001},
        {"unknown": 1},
    ],
)
def test_policy_rejects_invalid_values(values):
    from feishu.worker import WorkerPolicy

    with pytest.raises(ValidationError):
        WorkerPolicy(**values)


def test_budget_rejects_short_default_lease():
    from feishu.worker import Dispatcher

    dedup = Dedup()
    dedup.policy = DedupPolicy()
    with pytest.raises(ValueError, match="budget"):
        Dispatcher(research=Service(), dedup=dedup, sink=Sink())


def test_real_graph_reused_with_independent_request_state():
    from clinical_agent.application.research import ResearchService
    from feishu.worker import Dispatcher

    class Retriever:
        def retrieve(self, request):
            return RetrievalResult(
                options=request.options, embedding_info=retrieval_embedding_info(), hits=[]
            )

    class Generator:
        def generate(self, *args, **kwargs):
            raise AssertionError("empty retrieval must not generate")

    from clinical_agent.application.pico import PicoPlanner
    from tests.unit.test_intent_routing import Extractor

    service = ResearchService(
        planner=PicoPlanner(extractor=Extractor("question_answer")),
        online_retriever=EmptyOnline(),
        retriever=Retriever(),
        generator=Generator(),
        now=lambda: datetime(2026, 10, 27, tzinfo=UTC),
    )
    graph = service._graph
    sink = Sink()
    worker = Dispatcher(research=service, dedup=Dedup(), sink=sink)
    try:
        messages = [envelope(1), envelope(2)]
        futures = [worker.submit(m).future for m in messages]
        assert [f.result(3).status for f in futures] == ["queued", "queued"]
        for delivery in sink.deliveries:
            request = QuestionRequest(
                question=delivery.envelope.text,
                request_id=delivery.envelope.request_id,
                scope="hybrid",
            )
            assert delivery.answer == service.answer(request)
        assert service._graph is graph
    finally:
        assert worker.close(timeout_seconds=5)


def test_cancel_before_start_releases_exactly_once(setup_worker, monkeypatch):
    from concurrent.futures import Future

    worker, service, dedup, sink = setup_worker
    pending = Future()
    original = worker._executor.submit
    monkeypatch.setattr(worker._executor, "submit", lambda *args: pending)
    task = worker.submit(envelope())
    assert task.future.cancel()
    assert len([c for c in dedup.calls if c[0] == "release"]) == 1
    assert not service.requests and not sink.deliveries
    monkeypatch.setattr(worker._executor, "submit", original)
    assert worker.submit(envelope()).future.result(3).status == "queued"


def test_input_snapshot_and_invalid_input_before_io(setup_worker):
    worker, service, dedup, sink = setup_worker
    with pytest.raises(ValidationError):
        worker.submit({"text": "private"})
    assert not dedup.calls
    service.finish.clear()
    message = envelope()
    original = message.model_copy(deep=True)
    task = worker.submit(message)
    assert service.entered.wait(3)
    message.text = "Changed by caller"
    service.finish.set()
    assert task.future.result(3).status == "queued"
    assert sink.deliveries[0].envelope == original


def test_distinct_messages_never_exceed_capacity():
    from feishu.worker import Dispatcher, WorkerPolicy

    service, dedup, sink = Service(), Dedup(), Sink()
    service.finish.clear()
    worker = Dispatcher(research=service, dedup=dedup, sink=sink, policy=WorkerPolicy(capacity=2))
    try:
        tasks = [worker.submit(envelope(i)) for i in range(6)]
        assert [t.status for t in tasks] == ["accepted", "accepted"] + ["busy"] * 4
        assert len(dedup.owners) == 2
        service.finish.set()
        assert [t.future.result(3).status for t in tasks[:2]] == ["queued", "queued"]
    finally:
        service.finish.set()
        assert worker.close(timeout_seconds=5)


@pytest.mark.parametrize("when", ["acquire", "check"])
def test_redis_time_counts_toward_deadline(setup_worker, monkeypatch, when):
    worker, service, dedup, sink = setup_worker
    now = [0.0]
    worker._clock = lambda: now[0]
    original = getattr(dedup, when)

    def slow(*args):
        result = original(*args)
        now[0] = 91.0
        return result

    monkeypatch.setattr(dedup, when, slow)
    assert worker.submit(envelope()).future.result(3).status == "timed_out"
    assert not service.requests and not sink.deliveries and not dedup.owners


@pytest.mark.parametrize("timeout", [-1, True, "1", float("inf"), float("nan")])
def test_close_rejects_invalid_timeout(setup_worker, timeout):
    with pytest.raises(ValueError, match="timeout"):
        setup_worker[0].close(timeout_seconds=timeout)


@pytest.mark.parametrize("operation", ["acquire", "check", "release"])
def test_unexpected_adapter_errors_do_not_leak_or_overrelease(setup_worker, monkeypatch, operation):
    worker, _, _, sink = setup_worker

    def fail(*args):
        raise RuntimeError("private-secret")

    monkeypatch.setattr(worker._dedup, operation, fail)
    sink.accept = False
    task = worker.submit(envelope())
    if operation == "acquire":
        assert task.status == "unavailable"
    else:
        result = task.future.result(3)
        assert result.status == ("unavailable" if operation == "check" else "delivery_failed")
        assert "private" not in repr(result)


def test_real_graph_generation_keeps_evidence_for_each_message(prepared_factory):
    from clinical_agent.application.research import ResearchService
    from clinical_agent.domain.retrieval import DocumentSummary, EvidenceHit
    from feishu.worker import Dispatcher

    prepared = prepared_factory()
    chunk = prepared.embedded[0].evidence

    class Retriever:
        def retrieve(self, request):
            return RetrievalResult(
                options=request.options,
                embedding_info=retrieval_embedding_info(),
                hits=[
                    EvidenceHit(
                        chunk=chunk,
                        document=DocumentSummary.from_document(prepared.source.parsed.document),
                        score=1.0,
                        rank=1,
                    )
                ],
            )

    generation_barrier = Barrier(2)
    generation_lock = Lock()
    generation_calls = [0]

    class Generator:
        def generate(self, context, *, timeout_seconds):
            with generation_lock:
                generation_calls[0] += 1
                concurrent = generation_calls[0] <= 2
            if concurrent:
                generation_barrier.wait(3)
            assert timeout_seconds > 0
            return json.dumps(
                {
                    "claims": [
                        {
                            "text": context.question,
                            "kind": "evidence",
                            "evidence_chunk_ids": [str(chunk.chunk_id)],
                            "limitations": [],
                        }
                    ]
                }
            )

    from clinical_agent.application.pico import PicoPlanner
    from tests.unit.test_intent_routing import Extractor

    service = ResearchService(
        planner=PicoPlanner(extractor=Extractor("question_answer")),
        online_retriever=EmptyOnline(),
        retriever=Retriever(),
        generator=Generator(),
        now=lambda: datetime(2026, 10, 27, tzinfo=UTC),
    )
    sink = Sink()
    worker = Dispatcher(research=service, dedup=Dedup(), sink=sink)
    try:
        messages = [envelope(1), envelope(2)]
        messages[1].text = "Second synthetic question?"
        tasks = [worker.submit(m) for m in messages]
        assert [t.future.result(3).status for t in tasks] == ["queued", "queued"]
        for delivery in sink.deliveries:
            request = QuestionRequest(
                question=delivery.envelope.text,
                request_id=delivery.envelope.request_id,
                scope="hybrid",
            )
            assert delivery.answer == service.answer(request)
            assert delivery.answer.claims[0].text == delivery.envelope.text
            assert delivery.answer.sources[0].evidence[0].chunk_id == chunk.chunk_id
    finally:
        assert worker.close(timeout_seconds=5)


def test_handoff_carries_bounded_sender_deadline(setup_worker):
    worker, _, _, sink = setup_worker
    worker._clock = lambda: 100.0
    assert worker.submit(envelope()).future.result(3).status == "queued"
    assert sink.deliveries[0].deadline == 115.0


@pytest.mark.parametrize("code", ["extraction_failed", "generation_timeout", None])
def test_research_failure_logs_safe_code(setup_worker, caplog, code):
    import logging

    from clinical_agent.domain.research import ResearchError
    from feishu.main import _SafeFormatter

    worker, service, _, sink = setup_worker

    def fail(request):
        if code:
            raise ResearchError(code)
        raise RuntimeError("private-secret-question")

    service.answer = fail
    with caplog.at_level(logging.WARNING, logger="feishu.worker"):
        message = envelope()
        worker.submit(message).future.result(timeout=5)
    record = next(r for r in caplog.records if r.msg == "feishu_research_failed")
    data = json.loads(_SafeFormatter().format(record))
    assert data["request_id"] == str(message.request_id)
    assert data["error_code"] == (code or "research_failed")
    assert "private-secret" not in json.dumps(data)
    assert sink.deliveries[0].error_code == "research_failed"


@pytest.mark.parametrize("explicit", [False, True])
def test_report_delivery_uses_selected_entry(setup_worker, case, explicit):
    from clinical_agent.domain.report import ReportResult
    from tests.unit.test_feedback_agents import service as report_service

    worker, research, _, sink = setup_worker
    message = envelope()
    if explicit:
        message.text = "/report test direction"
    svc, _, _, _ = report_service(case, ["supported"])
    request = case[0].model_copy(update={"request_id": message.request_id})
    result = svc.report(request).report
    calls = []

    def respond(request):
        calls.append(("respond", request.question))
        return result

    def report(request):
        calls.append(("report", request.question))
        return ReportResult(report=result, markdown="synthetic")

    research.respond, research.report = respond, report
    worker.submit(message).future.result(timeout=5)
    assert (
        calls == [("report", "test direction")]
        if explicit
        else calls == [("respond", message.text)]
    )
    assert sink.deliveries[0].answer == result
