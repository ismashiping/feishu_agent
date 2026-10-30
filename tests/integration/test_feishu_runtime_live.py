"""Opt-in real SDK/Redis/message smoke; synthetic research, explicit nonce only."""

import asyncio
import os
import signal
from datetime import UTC, datetime
from threading import Event, Timer

import pytest

pytestmark = [pytest.mark.external, pytest.mark.integration, pytest.mark.redis]


def test_official_long_connection_and_reply(monkeypatch, tmp_path):
    from clinical_agent.domain.research import ResearchAnswer
    from feishu import main
    from feishu.dedup import DedupPolicy, create_deduplicator
    from feishu.events import EventPolicy, filter_event
    from feishu.sender import OfficialMessageAPI, Sender
    from feishu.worker import Dispatcher

    if os.environ.get("CLINICAL_AGENT_FEISHU_LIVE_CONFIRM") != "1":
        pytest.skip("Explicit live test confirmation is required")
    nonce = os.environ["CLINICAL_AGENT_FEISHU_LIVE_NONCE"]
    live_timeout = int(os.environ.get("CLINICAL_AGENT_FEISHU_LIVE_TIMEOUT_SECONDS", "180"))
    assert 1 <= live_timeout <= 600
    settings = main.FeishuSettings(model_dir=tmp_path)
    completed, connected, received = Event(), Event(), Event()
    results = []

    class SyntheticResearch:
        def respond(self, request):
            return ResearchAnswer(
                request_id=request.request_id,
                status="insufficient_evidence",
                claims=[],
                sources=[],
                limitations=["P1-16 合成冒烟测试，未执行医学检索。"],
                generated_at=datetime.now(UTC),
            )

    def stop():
        handler = signal.getsignal(signal.SIGTERM)
        if callable(handler):
            handler(signal.SIGTERM, None)

    original_factory = main.create_sdk_client

    def factory(*args):
        client = original_factory(*args)
        original_connect = client._connect

        def ready():
            connected.set()
            print("P116_LIVE_CONNECTED: send the agreed nonce to the test bot.", flush=True)

        async def connect():
            await original_connect()
            ready()

        client._connect = connect
        return client

    monkeypatch.setattr(main, "create_sdk_client", factory)
    asyncio.set_event_loop(asyncio.new_event_loop())
    dedup = create_deduplicator(
        settings.redis_url.get_secret_value(),
        policy=DedupPolicy(prefix="p116-live-smoke", lease_ms=120000, max_processing_ms=120000),
    )
    original_complete = dedup.complete

    def complete(lease):
        result = original_complete(lease)
        results.append(result)
        completed.set()
        stop()
        return result

    monkeypatch.setattr(dedup, "complete", complete)
    watchdog = Timer(live_timeout, stop)
    watchdog.daemon = True
    try:
        with main.create_http_client() as http:
            sender = Sender(
                dedup=dedup,
                transport=OfficialMessageAPI(http, token=main.TenantToken(settings, http)),
            )
            dispatcher = Dispatcher(research=SyntheticResearch(), dedup=dedup, sink=sender)
            runtime = main.BotRuntime(dispatcher, sender, lambda: None)
            receiver = main.Receiver(settings, dispatcher, sender)
            policy = EventPolicy(app_id=settings.app_id, bot_open_id=settings.bot_open_id)

            def receive(data):
                decision = filter_event(main._payload(data), policy=policy)
                print(f"P116_LIVE_EVENT: {decision.status}/{decision.reason}", flush=True)
                if decision.envelope is not None and decision.envelope.text == nonce:
                    received.set()
                    receiver(data)

            watchdog.start()
            try:
                main.run_sdk(settings, receive)
            finally:
                watchdog.cancel()
                assert runtime.close(timeout_seconds=10), "Live workers did not drain"
    finally:
        watchdog.cancel()
        dedup.close()
    assert connected.is_set(), "No real SDK connection"
    assert received.is_set(), "No matching test nonce received"
    assert completed.is_set() and results == ["owned"], (
        "No confirmed message reply and owner completion"
    )
    print(
        "P116_LIVE_SENT: real SDK receive, official message success and Redis owner complete.",
        flush=True,
    )
