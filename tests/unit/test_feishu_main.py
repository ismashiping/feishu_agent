"""Runtime boundaries use synthetic SDK DTOs and explicit offline substitutes."""

import asyncio
import json
import logging
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from pydantic import ValidationError


def settings(tmp_path, **kw):
    from feishu.main import FeishuSettings

    return FeishuSettings(
        app_id="cli_test",
        app_secret="SECRET_SENTINEL",
        bot_open_id="ou_bot",
        model_dir=tmp_path,
        redis_url="redis://localhost:6379/4",
        **kw,
    )


def payload(**message):
    return {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1", "app_id": "cli_test", "event_id": "ev_1"},
        "event": {
            "sender": {"sender_type": "user", "sender_id": {"open_id": "ou_user"}},
            "message": {
                "message_id": "om_1",
                "chat_id": "oc_1",
                "chat_type": "p2p",
                "message_type": "text",
                "content": '{"text":"question"}',
                **message,
            },
        },
    }


def sdk_event(data):
    from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

    return P2ImMessageReceiveV1(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("capacity", 0),
        ("capacity", True),
        ("sender_capacity", 65),
        ("shutdown_seconds", -1),
        ("shutdown_seconds", float("inf")),
    ],
)
def test_invalid_policy(tmp_path, field, value):
    with pytest.raises(ValidationError):
        settings(tmp_path, **{field: value})


def test_settings_env_and_secrets(tmp_path, monkeypatch):
    from feishu.main import FeishuSettings

    for key, value in {
        "APP_ID": "cli_test",
        "APP_SECRET": "SECRET_SENTINEL",
        "BOT_OPEN_ID": "ou_bot",
        "MODEL_DIR": str(tmp_path),
        "REDIS_URL": "redis://:SECRET_SENTINEL@localhost/4",
        "CAPACITY": "3",
    }.items():
        monkeypatch.setenv("CLINICAL_AGENT_FEISHU_" + key, value)
    selected = FeishuSettings()
    assert selected.capacity == 3
    assert "SECRET_SENTINEL" not in repr(selected)
    monkeypatch.setenv("CLINICAL_AGENT_FEISHU_CAPACITY", "SECRET_SENTINEL")
    with pytest.raises(ValidationError) as error:
        FeishuSettings()
    assert "SECRET_SENTINEL" not in str(error.value)


@pytest.mark.parametrize(
    "url", ["http://localhost", "redis://localhost/0?socket_timeout=0", "redis://localhost/#x"]
)
def test_invalid_redis_url(tmp_path, url):
    from feishu.main import FeishuSettings

    with pytest.raises(ValidationError):
        FeishuSettings(
            app_id="cli_test",
            app_secret="x",
            bot_open_id="ou_bot",
            model_dir=tmp_path,
            redis_url=url,
        )


@pytest.mark.parametrize(
    "status,notice",
    [
        ("accepted", None),
        ("duplicate", None),
        ("closed", None),
        ("busy", "busy"),
        ("unavailable", "unavailable"),
        ("submit_failed", "unavailable"),
    ],
)
def test_sdk_callback_routes_without_waiting(tmp_path, status, notice):
    from feishu.main import Receiver

    dispatcher, sender = Mock(), Mock()
    dispatcher.submit.return_value = SimpleNamespace(status=status, future=Mock())
    receiver = Receiver(settings(tmp_path), dispatcher, sender)
    assert receiver(sdk_event(payload())) is None
    envelope = dispatcher.submit.call_args.args[0]
    assert envelope.text == "question" and envelope.event_id == "ev_1"
    assert not dispatcher.submit.return_value.future.result.called
    if notice:
        sender.offer_notice.assert_called_once_with(envelope, notice)
    else:
        sender.offer_notice.assert_not_called()


@pytest.mark.parametrize(
    "mutation",
    ["bot", "self", "image", "group", "missing_header", "schema", "other_app", "bad_content"],
)
def test_callback_filters_sdk_objects(tmp_path, mutation):
    from feishu.main import Receiver

    p = payload()
    if mutation == "bot":
        p["event"]["sender"]["sender_type"] = "bot"
    if mutation == "self":
        p["event"]["sender"]["sender_id"]["open_id"] = "ou_bot"
    if mutation == "image":
        p["event"]["message"]["message_type"] = "image"
    if mutation == "group":
        p["event"]["message"]["chat_type"] = "group"
    if mutation == "missing_header":
        p.pop("header")
    if mutation == "schema":
        p["schema"] = "1.0"
    if mutation == "other_app":
        p["header"]["app_id"] = "other"
    if mutation == "bad_content":
        p["event"]["message"]["content"] = "broken"
    dispatcher, sender = Mock(), Mock()
    Receiver(settings(tmp_path), dispatcher, sender)(sdk_event(p))
    dispatcher.submit.assert_not_called()
    sender.offer_notice.assert_not_called()


def test_sdk_group_mention(tmp_path):
    from feishu.main import Receiver

    dispatcher, sender = Mock(), Mock()
    Receiver(settings(tmp_path), dispatcher, sender)(
        sdk_event(
            payload(
                chat_type="group",
                content='{"text":"@_user_1 question"}',
                mentions=[{"key": "@_user_1", "id": {"open_id": "ou_bot"}}],
            )
        )
    )
    assert dispatcher.submit.call_args.args[0].text == "question"


def test_callback_exception_is_private(tmp_path, caplog):
    from feishu.main import Receiver

    dispatcher = Mock()
    dispatcher.submit.side_effect = RuntimeError("SECRET_SENTINEL")
    with caplog.at_level(logging.INFO, logger="feishu"):
        Receiver(settings(tmp_path), dispatcher, Mock())(sdk_event(payload()))
    assert "SECRET_SENTINEL" not in caplog.text
    assert "callback_failed" in caplog.text


def test_token_protocol_and_deadline(tmp_path):
    from feishu.main import TenantToken

    calls = []

    def respond(request):
        calls.append(request)
        assert (
            str(request.url)
            == "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        )
        assert json.loads(request.content) == {
            "app_id": "cli_test",
            "app_secret": "SECRET_SENTINEL",
        }
        assert "authorization" not in request.headers
        assert request.extensions["timeout"]["read"] <= 3
        return httpx.Response(200, json={"code": 0, "tenant_access_token": "token", "expire": 7200})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        token = TenantToken(settings(tmp_path), client, clock=lambda: 10)
        assert token(13) == token(13) == "token"
        with pytest.raises(ValueError):
            token(10)
    assert len(calls) == 2  # no additional token cache


@pytest.mark.parametrize(
    "body,status",
    [
        ({"code": 1}, 200),
        ({"code": False, "tenant_access_token": "t", "expire": 7200}, 200),
        ({"code": 0, "tenant_access_token": "a b", "expire": 7200}, 200),
        ({"code": 0, "tenant_access_token": "t", "expire": 0}, 200),
        ({"code": 0, "tenant_access_token": "t", "expire": True}, 200),
        ({"code": 0, "tenant_access_token": "t", "expire": 7200}, 302),
        ({}, 500),
    ],
)
def test_token_rejects_failure(tmp_path, body, status):
    from feishu.main import TenantToken

    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(status, json=body))
    ) as client:
        with pytest.raises(ValueError, match="Token unavailable"):
            TenantToken(settings(tmp_path), client, clock=lambda: 0)(5)


def test_token_rejects_late_success(tmp_path):
    from feishu.main import TenantToken

    clock = iter([0, 10])
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t", "expire": 7200}
            )
        )
    ) as client:
        with pytest.raises(ValueError):
            TenantToken(settings(tmp_path), client, clock=lambda: next(clock))(5)


def test_shutdown_order_timeout_and_idempotency():
    from feishu.main import BotRuntime

    order = []
    worker, sender = Mock(), Mock()
    worker.close.side_effect = [False, True]
    sender.close.side_effect = [False, True]
    runtime = BotRuntime(worker, sender, lambda: order.append("resources"))
    assert runtime.close(timeout_seconds=0) is False
    sender.close.assert_not_called()
    assert order == []
    assert runtime.close(timeout_seconds=0) is False
    assert order == []
    assert runtime.close(timeout_seconds=0) is True
    assert runtime.close(timeout_seconds=0) is True
    assert order == ["resources"]


def test_composition_rollback_and_shared_service(tmp_path, monkeypatch):
    import feishu.main as main

    order = []
    research = Mock()

    @contextmanager
    def open_research(path):
        assert path == tmp_path
        order.append("research_open")
        try:
            yield research
        finally:
            order.append("research_close")

    dedup = Mock()
    dedup.policy = main.DedupPolicy(lease_ms=120000, max_processing_ms=120000)
    dedup.close.side_effect = lambda: order.append("redis_close")
    client = Mock()
    client.close.side_effect = lambda: order.append("http_close")
    monkeypatch.setattr(main, "open_research", open_research)
    monkeypatch.setattr(main, "create_deduplicator", lambda *a, **k: dedup)
    monkeypatch.setattr(main, "create_http_client", lambda: client)
    runtime = main.build_runtime(settings(tmp_path))
    assert runtime.dispatcher._research is research
    assert runtime.dispatcher._sink is runtime.sender
    assert runtime.close(timeout_seconds=2)
    assert order == ["research_open", "http_close", "redis_close", "research_close"]
    monkeypatch.setattr(main, "Sender", Mock(side_effect=RuntimeError("synthetic")))
    with pytest.raises(RuntimeError):
        main.build_runtime(settings(tmp_path))
    assert order[-3:] == ["http_close", "redis_close", "research_close"]


def test_http_client_is_explicit():
    from feishu.main import create_http_client

    with create_http_client() as client:
        assert client.follow_redirects is False
        assert client.trust_env is False
        assert not client.params
        assert client.auth is None
        assert "authorization" not in client.headers
        assert client.event_hooks == {"request": [], "response": []}
        assert client._transport._pool._retries == 0


def test_sdk_discovery_uses_bounded_http_and_real_handler(tmp_path):
    from lark_oapi.ws import client as ws

    from feishu.main import create_sdk_client

    loop = ws.loop
    asyncio.set_event_loop(loop)
    seen = []

    def respond(request):
        assert str(request.url) == "https://open.feishu.cn/callback/ws/endpoint"
        assert request.extensions["timeout"]["read"] == 5
        assert json.loads(request.content)["AppID"] == "cli_test"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "URL": "wss://example.invalid/ws?service_id=1&device_id=x",
                    "ClientConfig": {
                        "PingInterval": 30,
                        "ReconnectInterval": 5,
                        "ReconnectNonce": 1,
                        "ReconnectCount": 2,
                    },
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        sdk = create_sdk_client(settings(tmp_path), seen.append, client)
        try:
            assert sdk._get_conn_url().startswith("wss://example.invalid")
            assert sdk._ping_interval == 30
            sdk._event_handler._do_without_validation(json.dumps(payload()).encode())
            assert len(seen) == 1
            assert seen[0].header.app_id == "cli_test"
        finally:
            sdk._cache._cron.cancel()
            loop.run_until_complete(asyncio.sleep(0))


@pytest.mark.parametrize("fails", [False, True])
def test_sdk_serve_cancels_tasks_and_disconnects(fails):
    from feishu.main import serve_sdk

    order = []

    async def run():
        stop = asyncio.Event()

        class Client:
            async def _connect(self):
                order.append("connect")
                if fails:
                    raise RuntimeError("synthetic")
                asyncio.create_task(stop_soon())

            async def _ping_loop(self):
                try:
                    await asyncio.sleep(100)
                finally:
                    order.append("cancel")

            async def _disconnect(self):
                order.append("disconnect")

        async def stop_soon():
            await asyncio.sleep(0)
            stop.set()

        await serve_sdk(Client(), stop)

    if fails:
        with pytest.raises(RuntimeError):
            asyncio.run(run())
    else:
        asyncio.run(run())
        assert "cancel" in order
    assert order[-1] == "disconnect"


def test_entry_help_and_failure_are_private(monkeypatch, capsys):
    import feishu.main as main

    assert main.main(["--help"]) == 0
    assert "Clinical" in capsys.readouterr().out
    monkeypatch.setattr(main, "FeishuSettings", Mock(side_effect=ValueError("SECRET_SENTINEL")))
    assert main.main([]) == 1
    assert "SECRET_SENTINEL" not in capsys.readouterr().err


def test_sdk_background_terminal_failure_is_not_hidden():
    from feishu.main import serve_sdk

    async def run():
        class Client:
            async def _connect(self):
                async def broken():
                    await asyncio.sleep(0)
                    raise RuntimeError("synthetic terminal failure")

                asyncio.create_task(broken())

            async def _ping_loop(self):
                await asyncio.sleep(100)

            async def _disconnect(self):
                pass

        with pytest.raises(RuntimeError, match="SDK background failure"):
            await asyncio.wait_for(serve_sdk(Client(), asyncio.Event()), timeout=1)

    asyncio.run(run())


def test_real_receiver_worker_sender_chain(tmp_path):
    from datetime import UTC, datetime
    from threading import Event
    from uuid import uuid4

    from clinical_agent.domain.research import ResearchAnswer
    from feishu.dedup import AcquireResult, DedupPolicy, Lease
    from feishu.main import BotRuntime, Receiver, TenantToken
    from feishu.sender import OfficialMessageAPI, Sender
    from feishu.worker import Dispatcher

    complete = Event()
    calls, requests = [], []

    class Research:
        def answer(self, request):
            calls.append(request)
            return ResearchAnswer(
                request_id=request.request_id,
                status="insufficient_evidence",
                claims=[],
                sources=[],
                limitations=["synthetic"],
                generated_at=datetime.now(UTC),
            )

    class Dedup:
        policy = DedupPolicy(lease_ms=120000, max_processing_ms=120000)
        taken = False

        def acquire(self, identity):
            if self.taken:
                return AcquireResult("duplicate")
            self.taken = True
            return AcquireResult("acquired", Lease(identity=identity, owner=uuid4()))

        def check(self, lease):
            return "owned"

        def complete(self, lease):
            complete.set()
            return "owned"

        def release(self, lease):
            return "owned"

    def respond(request):
        requests.append(request)
        if "/auth/" in request.url.path:
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "synthetic-token", "expire": 7200}
            )
        return httpx.Response(200, json={"code": 0, "data": {"message_id": "reply_1"}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        dedup = Dedup()
        sender = Sender(
            dedup=dedup,
            transport=OfficialMessageAPI(client, token=TenantToken(settings(tmp_path), client)),
        )
        worker = Dispatcher(research=Research(), dedup=dedup, sink=sender)
        runtime = BotRuntime(worker, sender, lambda: None)
        try:
            receiver = Receiver(settings(tmp_path), worker, sender)
            receiver(sdk_event(payload()))
            receiver(sdk_event(payload()))
            assert complete.wait(3)
        finally:
            assert runtime.close(timeout_seconds=3)
    assert len(calls) == 1
    assert len(requests) == 2
    assert requests[-1].url.path.endswith("/om_1/reply")
    assert "证据不足" in json.loads(json.loads(requests[-1].content)["content"])["text"]


@pytest.mark.parametrize("fail", [False, True])
def test_sdk_runner_restores_signals_logger_and_loop(tmp_path, monkeypatch, fail):
    import signal

    from lark_oapi.core.log import logger
    from lark_oapi.ws import client as ws

    import feishu.main as main

    original = {n: signal.getsignal(n) for n in (signal.SIGINT, signal.SIGTERM)}
    disabled = logger.disabled

    class Client:
        async def _connect(self):
            assert logger.disabled
            if fail:
                raise RuntimeError("synthetic")
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)

        async def _ping_loop(self):
            await asyncio.sleep(100)

        async def _disconnect(self):
            pass

    monkeypatch.setattr(main, "create_sdk_client", lambda *args: Client())
    if fail:
        with pytest.raises(RuntimeError):
            main.run_sdk(settings(tmp_path), Mock())
    else:
        main.run_sdk(settings(tmp_path), Mock())
    assert {n: signal.getsignal(n) for n in original} == original
    assert logger.disabled == disabled
    assert ws.loop.is_closed()


def test_official_sdk_data_frame_acknowledges_synthetic_event(tmp_path):
    from unittest.mock import AsyncMock

    from lark_oapi.ws import client as ws
    from lark_oapi.ws.pb.pbbp2_pb2 import Frame

    from feishu.main import create_sdk_client

    if ws.loop.is_closed():
        ws.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ws.loop)
    seen = []
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as http:
        sdk = create_sdk_client(settings(tmp_path), seen.append, http)
        sdk._write_message = AsyncMock()
        frame = Frame()
        frame.SeqID, frame.LogID, frame.service, frame.method = 1, 1, 1, 1
        for key, value in {
            "message_id": "frame_1",
            "trace_id": "trace_1",
            "sum": "1",
            "seq": "0",
            "type": "event",
        }.items():
            h = frame.headers.add()
            h.key, h.value = key, value
        frame.payload = json.dumps(payload()).encode()
        try:
            ws.loop.run_until_complete(sdk._handle_data_frame(frame))
            assert len(seen) == 1
            ack = Frame()
            ack.ParseFromString(sdk._write_message.call_args.args[0])
            assert json.loads(ack.payload)["code"] == 200
            assert any(header.key == "biz_rt" for header in ack.headers)
        finally:
            sdk._cache._cron.cancel()
            ws.loop.run_until_complete(asyncio.sleep(0))
            ws.loop.close()
            asyncio.set_event_loop(None)


def test_feishu_logs_keep_out_secrets_and_exception_text(capsys):
    from datetime import datetime

    from feishu.main import configure_feishu_logging

    logger = logging.getLogger("feishu")
    handlers, level, propagate = tuple(logger.handlers), logger.level, logger.propagate
    try:
        configure_feishu_logging("INFO")
        configure_feishu_logging("INFO")
        try:
            raise RuntimeError("SECRET_SENTINEL")
        except RuntimeError:
            logging.getLogger("feishu.sender").exception(
                "feishu_delivery",
                extra={
                    "request_id": "synthetic",
                    "status": "sent",
                    "dedup_status": "owned",
                    "payload": "SECRET_SENTINEL",
                },
            )
        output = capsys.readouterr().err
        assert "SECRET_SENTINEL" not in output and "Traceback" not in output
        data = json.loads(output)
        assert data["event"] == "feishu_delivery" and data["status"] == "sent"
        assert datetime.fromisoformat(data["timestamp"]).utcoffset().total_seconds() == 0
    finally:
        for handler in tuple(logger.handlers):
            if handler not in handlers:
                logger.removeHandler(handler)
                handler.close()
        logger.handlers = list(handlers)
        logger.setLevel(level)
        logger.propagate = propagate


def test_entry_cleanup_error_is_private_and_nonzero(tmp_path, monkeypatch, capsys):
    import feishu.main as main

    selected = settings(tmp_path)
    runtime = Mock()
    runtime.close.side_effect = RuntimeError("SECRET_SENTINEL")
    monkeypatch.setattr(main, "FeishuSettings", Mock(return_value=selected))
    monkeypatch.setattr(main, "build_runtime", Mock(return_value=runtime))
    monkeypatch.setattr(main, "run_sdk", Mock())
    monkeypatch.setattr(main, "configure_feishu_logging", Mock())
    assert main.main([]) == 1
    assert "SECRET_SENTINEL" not in capsys.readouterr().err


def test_entrypoint_alias_keeps_connection_log_in_configured_handler(capsys):
    import runpy
    from pathlib import Path

    logger = logging.getLogger("feishu")
    handlers, level, propagate = tuple(logger.handlers), logger.level, logger.propagate
    try:
        # python -m executes this source under __main__, unlike ordinary imports.
        # An inert alias exercises that naming behavior without launching clients.
        source = Path(__file__).resolve().parents[2] / "src/feishu/main.py"
        module = runpy.run_path(str(source), run_name="__entrypoint_probe__")
        module["configure_feishu_logging"]("INFO")
        module["_LOG"].info("feishu_connected")
        output = capsys.readouterr().err
        assert output, "Module entrypoint lost its connection event"
        assert json.loads(output)["event"] == "feishu_connected"
    finally:
        for handler in tuple(logger.handlers):
            if handler not in handlers:
                logger.removeHandler(handler)
                handler.close()
        logger.handlers = list(handlers)
        logger.setLevel(level)
        logger.propagate = propagate
