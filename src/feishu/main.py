"""Explicit Feishu composition and the version-pinned official SDK lifecycle seam."""

import argparse
import asyncio
import json
import logging
import signal
import sys
from collections.abc import Callable
from contextlib import ExitStack
from datetime import UTC, datetime
from importlib.metadata import version
from math import isfinite
from threading import RLock
from time import monotonic
from typing import TYPE_CHECKING, Annotated, Any, cast
from urllib.parse import urlsplit

from pydantic import DirectoryPath, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from clinical_agent.command_runtime import open_research
from clinical_agent.config import load_settings
from feishu.dedup import DedupPolicy, create_deduplicator
from feishu.events import EventPolicy, Identifier, filter_event
from feishu.sender import OfficialMessageAPI, Sender, SenderPolicy
from feishu.worker import Dispatcher, WorkerPolicy

if TYPE_CHECKING:
    import httpx

_LOG = logging.getLogger("feishu.main")


class FeishuSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLINICAL_AGENT_FEISHU_",
        env_file=None,
        extra="forbid",
        hide_input_in_errors=True,
        revalidate_instances="always",
    )
    app_id: Identifier
    app_secret: SecretStr = Field(min_length=1, repr=False)
    bot_open_id: Identifier
    model_dir: DirectoryPath
    redis_url: SecretStr = Field(min_length=1, repr=False)
    capacity: Annotated[int, Field(strict=True, ge=1, le=4)] = 2
    sender_capacity: Annotated[int, Field(strict=True, ge=1, le=64)] = 8
    shutdown_seconds: Annotated[float, Field(ge=0, le=120, allow_inf_nan=False)] = 5.0

    @field_validator("capacity", "sender_capacity", mode="before")
    @classmethod
    def environment_integer(cls, value: object) -> object:
        return (
            int(value)
            if isinstance(value, str) and value.isascii() and value.isdecimal()
            else value
        )

    @field_validator("redis_url")
    @classmethod
    def redis_endpoint(cls, value: SecretStr) -> SecretStr:
        try:
            raw = value.get_secret_value()
            url = urlsplit(raw)
            if (
                url.scheme not in {"redis", "rediss"}
                or not url.hostname
                or "?" in raw
                or "#" in raw
            ):
                raise ValueError
            _ = url.port
            if url.path not in {"", "/"} and not (
                url.path[1:].isascii() and url.path[1:].isdecimal()
            ):
                raise ValueError
        except ValueError:
            raise ValueError("Invalid Redis URL") from None
        return value


def _payload(data: Any) -> dict[str, object]:
    """Copy only the existing filter contract; SDK metadata never becomes a policy."""
    header, event = data.header, data.event
    sender, message = event.sender, event.message
    mentions = message.mentions
    return {
        "schema": data.schema,
        "header": {
            "event_type": header.event_type,
            "app_id": header.app_id,
            "event_id": header.event_id,
        },
        "event": {
            "sender": {
                "sender_type": sender.sender_type,
                "sender_id": {"open_id": getattr(sender.sender_id, "open_id", None)},
            },
            "message": {
                "message_id": message.message_id,
                "chat_id": message.chat_id,
                "chat_type": message.chat_type,
                "message_type": message.message_type,
                "content": message.content,
                "mentions": None
                if mentions is None
                else [
                    {"key": item.key, "id": {"open_id": getattr(item.id, "open_id", None)}}
                    for item in mentions
                ],
            },
        },
    }


class Receiver:
    def __init__(self, settings: FeishuSettings, dispatcher: Dispatcher, sender: Sender) -> None:
        self._policy = EventPolicy(app_id=settings.app_id, bot_open_id=settings.bot_open_id)
        self._dispatcher, self._sender = dispatcher, sender

    def __call__(self, data: object) -> None:
        try:
            decision = filter_event(_payload(data), policy=self._policy)
            if decision.envelope is None:
                return
            envelope = decision.envelope
            submitted = self._dispatcher.submit(envelope)
            if submitted.status == "busy":
                self._sender.offer_notice(envelope, "busy")
            elif submitted.status in {"unavailable", "submit_failed"}:
                self._sender.offer_notice(envelope, "unavailable")
            _LOG.info(
                "feishu_admission",
                extra={"request_id": str(envelope.request_id), "status": submitted.status},
            )
        except Exception:
            _LOG.warning("callback_failed")


class TenantToken:
    """A bounded, uncached official internal-app token request, off the SDK loop."""

    def __init__(
        self,
        settings: FeishuSettings,
        client: "httpx.Client",
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._settings, self._client, self._clock = settings, client, clock

    def __call__(self, deadline: float) -> str:
        try:
            remaining = deadline - self._clock()
            if not isfinite(remaining) or remaining <= 0:
                raise ValueError
            response = self._client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self._settings.app_id,
                    "app_secret": self._settings.app_secret.get_secret_value(),
                },
                timeout=min(5.0, remaining),
                follow_redirects=False,
            )
            data = response.json()
            token = data.get("tenant_access_token")
            if (
                response.status_code != 200
                or type(data.get("code")) is not int
                or data["code"] != 0
                or type(data.get("expire")) is not int
                or data["expire"] <= 0
                or not isinstance(token, str)
                or not token
                or any(c.isspace() for c in token)
                or self._clock() >= deadline
            ):
                raise ValueError
            return token
        except Exception:
            raise ValueError("Token unavailable") from None


def create_http_client() -> "httpx.Client":
    import httpx

    return httpx.Client(
        transport=httpx.HTTPTransport(retries=0),
        timeout=5.0,
        trust_env=False,
        follow_redirects=False,
        limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
    )


class BotRuntime:
    def __init__(
        self, dispatcher: Dispatcher, sender: Sender, close_resources: Callable[[], None]
    ) -> None:
        self.dispatcher, self.sender = dispatcher, sender
        self._close_resources = close_resources
        self._closed = False
        self._workers_drained = False
        self._lock = RLock()

    def close(self, *, timeout_seconds: float = 5.0) -> bool:
        if (
            isinstance(timeout_seconds, bool)
            or not isfinite(timeout_seconds)
            or timeout_seconds < 0
        ):
            raise ValueError("Invalid shutdown timeout")
        with self._lock:
            if self._closed:
                return True
            deadline = monotonic() + timeout_seconds
            if not self._workers_drained:
                self._workers_drained = self.dispatcher.close(
                    timeout_seconds=max(0, deadline - monotonic())
                )
                if not self._workers_drained:
                    return False
            if not self.sender.close(timeout_seconds=max(0, deadline - monotonic())):
                return False
            self._closed = True
            self._close_resources()
            return True


def build_runtime(settings: FeishuSettings) -> BotRuntime:
    settings = FeishuSettings.model_validate(settings)
    stack = ExitStack()
    sender = None
    try:
        research = stack.enter_context(open_research(settings.model_dir))
        dedup = create_deduplicator(
            settings.redis_url.get_secret_value(),
            policy=DedupPolicy(lease_ms=120000, max_processing_ms=120000),
        )
        stack.callback(dedup.close)
        client = create_http_client()
        stack.callback(client.close)
        sender = Sender(
            dedup=dedup,
            transport=OfficialMessageAPI(client, token=TenantToken(settings, client)),
            policy=SenderPolicy(capacity=settings.sender_capacity),
        )
        dispatcher = Dispatcher(
            research=research,
            dedup=dedup,
            sink=sender,
            policy=WorkerPolicy(capacity=settings.capacity),
        )
        return BotRuntime(dispatcher, sender, stack.close)
    except BaseException:
        if sender is not None:
            while not sender.close(timeout_seconds=1):
                pass
        stack.close()
        raise


def create_sdk_client(
    settings: FeishuSettings, callback: Callable[[object], None], client: "httpx.Client"
) -> Any:
    import lark_oapi as lark  # type: ignore[import-untyped]
    from lark_oapi.ws.model import EndpointResp  # type: ignore[import-untyped]

    class BoundedClient(lark.ws.Client):  # type: ignore[misc]
        def _get_conn_url(self) -> str:
            # SDK 1.7.5 discovery lacks a timeout. Keep its response/config objects.
            response = client.post(
                "https://open.feishu.cn/callback/ws/endpoint",
                json={
                    "AppID": settings.app_id,
                    "AppSecret": settings.app_secret.get_secret_value(),
                },
                timeout=5.0,
                follow_redirects=False,
            )
            if response.status_code != 200:
                raise ValueError("SDK discovery failed")
            data = response.json()
            if type(data.get("code")) is not int or data["code"] != 0:
                raise ValueError("SDK discovery failed")
            endpoint = EndpointResp(data).data
            if (
                endpoint is None
                or not isinstance(endpoint.URL, str)
                or not endpoint.URL.startswith("wss://")
            ):
                raise ValueError("SDK discovery failed")
            if endpoint.ClientConfig is not None:
                self._configure(endpoint.ClientConfig)
            return endpoint.URL

    handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(callback)
        .build()
    )
    return BoundedClient(
        settings.app_id,
        settings.app_secret.get_secret_value(),
        event_handler=handler,
        log_level=lark.LogLevel.ERROR,
    )


async def serve_sdk(client: Any, stop: asyncio.Event) -> None:
    """Run only on the dedicated CLI loop; every other task belongs to this SDK."""
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    failed = False

    def background_failed(_loop: asyncio.AbstractEventLoop, _context: dict[str, Any]) -> None:
        nonlocal failed
        failed = True
        stop.set()

    loop.set_exception_handler(background_failed)
    try:
        await client._connect()
        asyncio.create_task(client._ping_loop())
        _LOG.info("feishu_connected")
        await stop.wait()
        if failed:
            raise RuntimeError("SDK background failure")
    finally:
        try:
            tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.wait_for(client._disconnect(), timeout=3.0)
        finally:
            loop.set_exception_handler(previous_handler)


def run_sdk(settings: FeishuSettings, receiver: Receiver) -> None:
    if version("lark-oapi") != "1.7.5":
        raise RuntimeError("Unsupported SDK version")
    from lark_oapi.core.log import logger as sdk_logger  # type: ignore[import-untyped]
    from lark_oapi.ws import client as ws  # type: ignore[import-untyped]

    previous_disabled = sdk_logger.disabled
    loop = ws.loop
    if loop.is_closed():
        loop = ws.loop = asyncio.new_event_loop()
    if loop.is_running():
        raise RuntimeError("SDK requires a dedicated process loop")
    sdk_logger.disabled = True
    asyncio.set_event_loop(loop)
    previous_signals = {}
    try:
        stop = asyncio.Event()
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_signals[signum] = signal.getsignal(signum)
            signal.signal(signum, lambda *_: loop.call_soon_threadsafe(stop.set))
        with create_http_client() as http:
            client = create_sdk_client(settings, receiver, http)
            loop.run_until_complete(serve_sdk(client, stop))
    finally:
        for signum, handler in previous_signals.items():
            signal.signal(signum, handler)
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
        asyncio.set_event_loop(None)
        sdk_logger.disabled = previous_disabled


class _SafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "event": record.msg,
            "level": record.levelname.lower(),
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
        }
        for key in ("request_id", "status", "dedup_status"):
            value = getattr(record, key, None)
            if isinstance(value, str):
                data[key] = value
        return json.dumps(data, ensure_ascii=False)


def configure_feishu_logging(level: str) -> None:
    logger = logging.getLogger("feishu")
    for previous in tuple(logger.handlers):
        if previous.get_name() == "feishu.json":
            logger.removeHandler(previous)
            previous.close()
    handler = logging.StreamHandler(sys.stderr)
    handler.set_name("feishu.json")
    handler.setFormatter(_SafeFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clinical Literature Feishu bot")
    try:
        parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code or 0)
    runtime = None
    exit_code = 0
    try:
        settings = cast(Callable[[], FeishuSettings], FeishuSettings)()
        configure_feishu_logging(load_settings().log_level)
        runtime = build_runtime(settings)
        run_sdk(settings, Receiver(settings, runtime.dispatcher, runtime.sender))
    except KeyboardInterrupt:
        pass
    except Exception:
        print(
            "Feishu startup or connection failed; check configuration and service availability.",
            file=sys.stderr,
        )
        exit_code = 1
    finally:
        if runtime is not None:
            try:
                while not runtime.close(timeout_seconds=max(0.1, settings.shutdown_seconds)):
                    _LOG.warning("feishu_draining")
            except Exception:
                print("Feishu resource cleanup failed.", file=sys.stderr)
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
