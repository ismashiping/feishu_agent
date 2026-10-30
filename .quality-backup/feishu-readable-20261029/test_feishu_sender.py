"""Offline message protocol, citation rendering and bounded real sending thread."""

import json
import logging
from datetime import UTC, datetime
from threading import Event
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
import pytest

from clinical_agent.domain.research import ResearchAnswer
from feishu.dedup import AcquireResult, DedupPolicy, Lease
from feishu.events import MessageEnvelope
from feishu.worker import Delivery, Dispatcher


def message(index=1, *, event_only=False):
    identity = ("app", "event" if event_only else "message", f"id_{index}")
    return MessageEnvelope(
        app_id="app",
        message_id=None if event_only else identity[2],
        event_id=identity[2] if event_only else None,
        sender_id="user",
        chat_id="chat",
        chat_type="p2p",
        text="private-question",
        request_id=uuid5(NAMESPACE_URL, json.dumps(identity, separators=(",", ":"))),
    )


def answer(envelope=None, *, answered=False):
    envelope = envelope or message()
    chunk, document = uuid4(), uuid4()
    return ResearchAnswer.model_validate(
        dict(
            request_id=envelope.request_id,
            status="answered" if answered else "insufficient_evidence",
            claims=[
                dict(
                    claim_id="c1",
                    text="合成结论",
                    kind="inference",
                    evidence_chunk_ids=[chunk],
                    limitations=["结论局限"],
                )
            ]
            if answered
            else [],
            sources=[
                dict(
                    document_id=document,
                    title='合成<at user_id="all">题目</at>',
                    title_origin="manual",
                    authors=["Synthetic Author"],
                    publication_date=dict(precision="year", raw="2024", year=2024),
                    journal="Synthetic journal",
                    doi="10.0000/synthetic",
                    pmid="123456",
                    source_type="pubmed",
                    source_url="https://pubmed.ncbi.nlm.nih.gov/123456/",
                    content_hash="a" * 64,
                    content_scope="abstract",
                    evidence=[
                        dict(
                            chunk_id=chunk,
                            text="Synthetic evidence.",
                            location=dict(kind="abstract", section="RESULTS", start=0, end=19),
                        )
                    ],
                )
            ]
            if answered
            else [],
            limitations=["全局局限"],
            generated_at=datetime(2026, 10, 27, tzinfo=UTC),
        )
    )


def delivery(index=1, *, deadline=100.0):
    envelope = message(index)
    return Delivery(
        envelope, Lease(identity=envelope.dedup_identity, owner=uuid4()), deadline, answer(envelope)
    )


class Dedup:
    policy = DedupPolicy(lease_ms=120000)

    def __init__(self):
        self.calls = []
        self.checks = []
        self.cleanup = "owned"
        self.on_check = None

    def acquire(self, identity):
        self.calls.append("acquire")
        return AcquireResult("acquired", Lease(identity=identity, owner=uuid4()))

    def check(self, lease):
        self.calls.append("check")
        if self.on_check:
            self.on_check()
        result = self.checks.pop(0) if self.checks else "owned"
        if isinstance(result, Exception):
            raise result
        return result

    def complete(self, lease):
        self.calls.append("complete")
        if isinstance(self.cleanup, Exception):
            raise self.cleanup
        return self.cleanup

    def release(self, lease):
        self.calls.append("release")
        if isinstance(self.cleanup, Exception):
            raise self.cleanup
        return self.cleanup


class Transport:
    def __init__(self):
        self.calls = []
        self.entered, self.finish = Event(), Event()
        self.finish.set()
        self.result = "sent"

    def send(self, envelope, text, *, deadline, guard):
        self.entered.set()
        assert self.finish.wait(3)
        stopped = guard()
        if stopped:
            return stopped
        self.calls.append((envelope, text, deadline))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def rig():
    from feishu.sender import Sender, SenderPolicy

    dedup, transport, now = Dedup(), Transport(), [0.0]
    sender = Sender(
        dedup=dedup, transport=transport, policy=SenderPolicy(capacity=2), clock=lambda: now[0]
    )
    try:
        yield sender, dedup, transport, now
    finally:
        transport.finish.set()
        assert sender.close(timeout_seconds=3)


def test_render_preserves_claim_links_sources_and_limitations():
    from feishu.sender import render_answer

    dto = answer(answered=True)
    text = render_answer(dto)
    source = dto.sources[0]
    for expected in [
        "合成结论",
        "推断",
        "[1]",
        str(source.document_id),
        str(source.evidence[0].chunk_id),
        "RESULTS",
        "[0,19)",
        "摘要",
        "2024",
        "Synthetic Author",
        "Synthetic journal",
        "123456",
        "10.0000/synthetic",
        source.source_url,
        source.content_hash,
        "结论局限",
        "全局局限",
        "本地",
        "最新",
        "诊断",
    ]:
        assert expected in text
    assert "<at" not in text and "＜at" in text
    assert dto.sources[0].title.startswith("合成<at")


def test_render_pdf_location_unknown_metadata_and_shared_numbering():
    from feishu.sender import render_answer

    dto = answer(answered=True)
    source = dto.sources[0]
    source.source_type, source.content_scope = "pdf", "extracted_text"
    source.pmid = source.doi = source.source_url = source.journal = None
    source.authors = []
    source.publication_date = dict(precision="unknown")
    source.evidence[0].location = dict(kind="pdf_page", page=3, start=8, end=27)
    dto.claims.append(dto.claims[0].model_copy(update={"claim_id": "c2", "kind": "uncertainty"}))
    text = render_answer(dto)
    assert "第3页" in text and "[8,27)" in text and "PDF文本层" in text
    assert "未知" in text and "不确定" in text and "None" not in text
    assert text.count("[1]") == 3


def test_render_insufficient_and_utf8_overflow_is_whole_fallback():
    from feishu.sender import MAX_CONTENT_BYTES, render_answer, text_content

    assert "不代表" in render_answer(answer())
    dto = answer(answered=True)
    dto.sources[0].title = '中😀\n"' * 15000
    text = render_answer(dto)
    assert "过长" in text and "合成结论" not in text
    assert len(text_content(text).encode("utf-8")) <= MAX_CONTENT_BYTES
    assert json.loads(text_content('中文😀\n"')) == {"text": '中文😀\n"'}


def test_render_checks_outer_json_escaping_budget_too():
    from feishu.sender import render_answer

    dto = answer(answered=True)
    dto.sources[0].title = '"' * 9000
    assert "过长" in render_answer(dto)


@pytest.mark.parametrize(
    "url", ["file:///private.pdf", "https://name:secret@host/a", "javascript:x"]
)
def test_render_does_not_emit_unsafe_source_urls(url):
    from feishu.sender import render_answer

    dto = answer(answered=True)
    dto.sources[0].source_url = url
    assert url not in render_answer(dto)


def test_capacity_counts_running_and_waiting_close_and_snapshot(rig):
    sender, dedup, transport, _ = rig
    transport.finish.clear()
    first, second = delivery(1), delivery(2)
    assert sender.offer(first) and transport.entered.wait(2)
    assert sender.offer(second)
    second.envelope.chat_id = "changed"
    second.answer.limitations[0] = "changed"
    assert sender.offer(delivery(3)) is False
    assert sender.offer_notice(message(4), "busy") is False
    assert sender.close(timeout_seconds=0) is False
    assert not sender.offer(delivery(5))
    transport.finish.set()
    assert sender.close(timeout_seconds=3)
    assert len(transport.calls) == 2
    assert transport.calls[1][0].chat_id == "chat"
    assert "changed" not in transport.calls[1][1]
    assert dedup.calls.count("complete") == 2


@pytest.mark.parametrize(
    "result,cleanup",
    [
        ("sent", "complete"),
        ("failed", "release"),
        ("unknown", None),
        (RuntimeError("secret"), None),
    ],
)
def test_delivery_outcome_lease_action_and_private_logs(rig, caplog, result, cleanup):
    sender, dedup, transport, _ = rig
    caplog.set_level(logging.INFO, logger="feishu.sender")
    transport.result = result
    assert sender.offer(delivery()) and sender.close(timeout_seconds=3)
    assert dedup.calls.count("complete") == (cleanup == "complete")
    assert dedup.calls.count("release") == (cleanup == "release")
    assert "secret" not in caplog.text and "private-question" not in caplog.text
    record = next(r for r in caplog.records if r.name == "feishu.sender")
    assert record.request_id == str(message().request_id)
    assert record.status == ("unknown" if isinstance(result, Exception) else result)


@pytest.mark.parametrize("status", ["lost", "unavailable", RuntimeError("secret")])
def test_owner_guard_stops_without_cleanup(rig, status):
    sender, dedup, transport, _ = rig
    dedup.checks = [status]
    assert sender.offer(delivery()) and sender.close(timeout_seconds=3)
    assert not transport.calls and "complete" not in dedup.calls and "release" not in dedup.calls


def test_queue_expiry_and_post_check_budget(rig):
    sender, dedup, transport, now = rig
    transport.finish.clear()
    assert sender.offer(delivery(1)) and transport.entered.wait(2)
    assert sender.offer(delivery(2, deadline=1))
    now[0] = 2
    transport.finish.set()
    assert sender.close(timeout_seconds=3)
    assert len(transport.calls) == 1 and dedup.calls.count("release") == 1


def test_guard_after_slow_owner_check_prevents_send(rig):
    sender, dedup, transport, now = rig
    dedup.on_check = lambda: now.__setitem__(0, 100)
    assert sender.offer(delivery()) and sender.close(timeout_seconds=3)
    assert not transport.calls and dedup.calls[-1] == "release"


@pytest.mark.parametrize("cleanup", ["lost", "unavailable", RuntimeError("secret")])
def test_sent_cleanup_failure_never_retries(rig, cleanup):
    sender, dedup, transport, _ = rig
    dedup.cleanup = cleanup
    assert sender.offer(delivery()) and sender.close(timeout_seconds=3)
    assert len(transport.calls) == 1 and dedup.calls.count("complete") == 1
    assert "release" not in dedup.calls


@pytest.mark.parametrize("change", ["nan", "identity", "request", "both", "neither"])
def test_invalid_delivery_is_not_admitted(rig, change):
    sender, dedup, transport, _ = rig
    item = delivery()
    values = dict(
        envelope=item.envelope,
        lease=item.lease,
        deadline=item.deadline,
        answer=item.answer,
        error_code=item.error_code,
    )
    if change == "nan":
        values["deadline"] = float("nan")
    if change == "identity":
        values["lease"] = delivery(9).lease
    if change == "request":
        values["answer"] = answer(message(9))
    if change == "both":
        values["error_code"] = "research_failed"
    if change == "neither":
        values["answer"] = None
    with pytest.raises(ValueError, match="Invalid delivery"):
        sender.offer(Delivery(**values))
    assert not dedup.calls and not transport.calls


@pytest.mark.parametrize("code", ["busy", "unavailable", "invalid_input", "research_failed"])
def test_notices_are_bounded_without_fake_lease(rig, code):
    sender, dedup, transport, _ = rig
    assert sender.offer_notice(message(), code) and sender.close(timeout_seconds=3)
    assert len(transport.calls) == 1 and not dedup.calls
    assert "private-question" not in transport.calls[0][1]


@pytest.mark.parametrize(
    "field,value",
    [
        ("capacity", 0),
        ("capacity", True),
        ("capacity", 65),
        ("send_ms", 0),
        ("send_ms", 10001),
        ("notice_ms", 15001),
        ("notice_ms", "5"),
    ],
)
def test_strict_policy(field, value):
    from feishu.sender import SenderPolicy

    with pytest.raises(ValueError):
        SenderPolicy(**{field: value})


@pytest.mark.parametrize("timeout", [-1, True, float("inf"), float("nan"), "5"])
def test_invalid_close_timeout(rig, timeout):
    with pytest.raises(ValueError):
        rig[0].close(timeout_seconds=timeout)


@pytest.mark.parametrize("event_only", [False, True])
def test_official_api_routes_serialization_auth_and_timeout(event_only):
    from feishu.sender import OfficialMessageAPI

    requests, now, guards = [], [0.0], []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"code": 0, "data": {"message_id": "om_reply"}})

    def token(deadline):
        assert deadline == 5
        now[0] = 1
        return "private-token"

    def guard():
        guards.append(now[0])
        return None

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        api = OfficialMessageAPI(client, token=token, clock=lambda: now[0])
        assert (
            api.send(message(event_only=event_only), '中文😀\n"', deadline=5, guard=guard) == "sent"
        )
    request = requests[0]
    assert request.headers["Authorization"] == "Bearer private-token"
    assert request.url.host == "open.feishu.cn"
    assert request.url.path.endswith("/messages" if event_only else "/messages/id_1/reply")
    body = json.loads(request.content)
    assert body["msg_type"] == "text" and json.loads(body["content"]) == {"text": '中文😀\n"'}
    if event_only:
        assert body["receive_id"] == "chat" and request.url.params["receive_id_type"] == "chat_id"
    assert guards == [1]
    assert all(v == 4 for v in request.extensions["timeout"].values())


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (200, {"code": 0, "data": {"message_id": "om_ok"}}, "sent"),
        (200, {"code": 230001, "msg": "secret"}, "failed"),
        (400, {}, "failed"),
        (401, {}, "failed"),
        (429, {}, "failed"),
        (500, {}, "unknown"),
        (302, {}, "unknown"),
        (200, {"code": False, "data": {"message_id": "x"}}, "unknown"),
        (200, {"code": 0}, "unknown"),
        (200, {"code": "0"}, "unknown"),
        (200, [], "unknown"),
        (200, None, "unknown"),
    ],
)
def test_official_response_boundary(status, body, expected):
    from feishu.sender import OfficialMessageAPI

    calls = []

    def respond(request):
        calls.append(request)
        return (
            httpx.Response(status, json=body)
            if body is not None
            else httpx.Response(status, text="bad")
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        api = OfficialMessageAPI(client, token=lambda deadline: "token", clock=lambda: 0)
        assert api.send(message(), "text", deadline=5, guard=lambda: None) == expected
    assert len(calls) == 1


@pytest.mark.parametrize(
    "error", [httpx.ReadTimeout("secret"), httpx.ConnectError("secret"), httpx.WriteError("secret")]
)
def test_official_network_unknown_no_retry(error):
    from feishu.sender import OfficialMessageAPI

    calls = []

    def respond(request):
        calls.append(request)
        raise error

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        api = OfficialMessageAPI(client, token=lambda deadline: "token", clock=lambda: 0)
        assert api.send(message(), "text", deadline=5, guard=lambda: None) == "unknown"
    assert len(calls) == 1


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("token_error", "failed"),
        ("token_empty", "failed"),
        ("expired", "timed_out"),
        ("lost", "lost"),
    ],
)
def test_token_and_final_guard_prevent_http(mode, expected):
    from feishu.sender import OfficialMessageAPI

    calls, now = [], [0.0]

    def token(deadline):
        if mode == "token_error":
            raise RuntimeError("secret")
        if mode == "expired":
            now[0] = 5
        return "" if mode == "token_empty" else "token"

    def respond(request):
        calls.append(request)
        return httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        api = OfficialMessageAPI(client, token=token, clock=lambda: now[0])
        assert (
            api.send(
                message(), "text", deadline=5, guard=lambda: "lost" if mode == "lost" else None
            )
            == expected
        )
    assert not calls


@pytest.mark.parametrize("fail", [False, True])
def test_dispatcher_sender_handoff_and_error_reply(fail):
    from feishu.sender import Sender

    dedup, transport = Dedup(), Transport()
    transport.finish.clear()
    sender = Sender(dedup=dedup, transport=transport, clock=lambda: 0)

    class Service:
        def answer(self, request):
            if fail:
                raise RuntimeError("private-secret")
            return answer(answered=True)

    worker = Dispatcher(research=Service(), dedup=dedup, sink=sender, clock=lambda: 0)
    try:
        assert worker.submit(message()).future.result(3).status == "queued"
        assert transport.entered.wait(2) and "complete" not in dedup.calls
        assert worker.close(timeout_seconds=3)
        transport.finish.set()
        assert sender.close(timeout_seconds=3)
        assert dedup.calls.count("complete") == 1 and len(transport.calls) == 1
        assert "private-secret" not in transport.calls[0][1]
        assert ("失败" if fail else "合成结论") in transport.calls[0][1]
    finally:
        transport.finish.set()
        worker.close(timeout_seconds=3)
        sender.close(timeout_seconds=3)


def test_multiple_sources_keep_stable_numbers_and_exact_locations():
    from feishu.sender import render_answer

    dto = answer(answered=True)
    second = dto.sources[0].model_copy(deep=True)
    second.document_id, second.evidence[0].chunk_id = uuid4(), uuid4()
    second.title = "Second synthetic source"
    second.content_scope = "full_text"
    dto.sources.append(second)
    dto.claims[0].evidence_chunk_ids.insert(0, second.evidence[0].chunk_id)
    text = render_answer(dto)
    assert f"[2] chunk={second.evidence[0].chunk_id}" in text
    assert f"[1] chunk={dto.sources[0].evidence[0].chunk_id}" in text
    assert "[2] Second synthetic source" in text and "全文来源" in text


@pytest.mark.parametrize("state", ["lost", "unavailable"])
def test_sender_official_api_rechecks_owner_after_token_wait(state):
    from feishu.sender import OfficialMessageAPI, Sender

    calls, dedup = [], Dedup()

    def token(deadline):
        dedup.checks.append(state)
        return "token"

    def respond(request):
        calls.append(request)
        return httpx.Response(200)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        api = OfficialMessageAPI(client, token=token, clock=lambda: 0)
        sender = Sender(dedup=dedup, transport=api, clock=lambda: 0)
        try:
            assert sender.offer(delivery()) and sender.close(timeout_seconds=3)
            assert not calls and dedup.calls == ["check", "check", "check"]
        finally:
            sender.close(timeout_seconds=3)


def test_notice_queue_expiry_does_not_touch_redis(rig):
    sender, dedup, transport, now = rig
    transport.finish.clear()
    assert sender.offer(delivery()) and transport.entered.wait(2)
    assert sender.offer_notice(message(2), "busy")
    now[0] = 6
    transport.finish.set()
    assert sender.close(timeout_seconds=3)
    assert len(transport.calls) == 1 and dedup.calls.count("complete") == 1
    assert "release" not in dedup.calls


def test_unknown_transport_result_and_invalid_cleanup_are_conservative(rig, caplog):
    sender, dedup, transport, _ = rig
    caplog.set_level(logging.INFO, logger="feishu.sender")
    transport.result = "invalid-status-secret"
    assert sender.offer(delivery()) and sender.close(timeout_seconds=3)
    assert "complete" not in dedup.calls and "release" not in dedup.calls
    assert "invalid-status-secret" not in caplog.text


def test_failed_cleanup_error_is_contained_and_next_item_runs(rig):
    sender, dedup, transport, _ = rig
    dedup.cleanup = RuntimeError("secret")
    transport.result = "failed"
    assert sender.offer(delivery(1)) and sender.offer(delivery(2))
    assert sender.close(timeout_seconds=3)
    assert len(transport.calls) == 2 and dedup.calls.count("release") == 2


def test_official_api_initial_expiry_oversize_and_guard_exception_are_unsent():
    from feishu.sender import OfficialMessageAPI

    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200)

    def broken_guard():
        raise RuntimeError("secret")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        api = OfficialMessageAPI(client, token=lambda deadline: "token", clock=lambda: 0)
        assert api.send(message(), "text", deadline=0, guard=lambda: None) == "timed_out"
        assert api.send(message(), "中" * 24000, deadline=5, guard=lambda: None) == "failed"
        assert api.send(message(), '"' * 9000, deadline=5, guard=lambda: None) == "failed"
        assert api.send(message(), "text", deadline=5, guard=broken_guard) == "failed"
    assert not calls


def test_late_confirmed_response_is_completed_not_retried(caplog):
    from feishu.sender import OfficialMessageAPI, Sender

    caplog.set_level(logging.INFO, logger="feishu.sender")
    now, calls, dedup = [0.0], [], Dedup()

    def respond(request):
        calls.append(request)
        now[0] = 200
        return httpx.Response(200, json={"code": 0, "data": {"message_id": "reply"}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        api = OfficialMessageAPI(client, token=lambda deadline: "token", clock=lambda: now[0])
        sender = Sender(dedup=dedup, transport=api, clock=lambda: now[0])
        try:
            assert sender.offer(delivery()) and sender.close(timeout_seconds=3)
            assert len(calls) == 1 and dedup.calls[-1] == "complete"
        finally:
            sender.close(timeout_seconds=3)
