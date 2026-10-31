"""Plain text rendering, one bounded sending thread and official REST message API."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite
from queue import Empty, Queue
from threading import RLock, Thread
from time import monotonic
from typing import TYPE_CHECKING, Annotated, Literal, Protocol, get_args
from urllib.parse import urlsplit

from pydantic import Field, StrictInt

from clinical_agent.domain.models import DTO
from clinical_agent.domain.report import ResearchReport, render_report
from clinical_agent.domain.research import ResearchAnswer
from feishu.dedup import Lease, OperationResult
from feishu.events import MessageEnvelope
from feishu.worker import Delivery

if TYPE_CHECKING:
    import httpx

MAX_CONTENT_BYTES = 24000
MAX_BODY_BYTES = 30000
NOTICE = {
    "research_failed": "研究处理失败，请稍后再试。",
    "busy": "当前任务较多，请稍后再试。",
    "unavailable": "服务暂不可用，请稍后再试。",
    "invalid_input": "暂无法处理此输入，请发送有效文本问题。",
}
TOO_LONG = "结果过长，未展示结论及引用。请缩小问题范围后重试；本次仅检索本地文献。"
DISCLAIMER = (
    "仅检索本地已导入文献，不保证覆盖最新或全部研究；用于科研辅助，不用于个体诊断或治疗决策。"
)
NoticeCode = Literal["research_failed", "busy", "unavailable", "invalid_input"]
SendStatus = Literal["sent", "failed", "unknown", "timed_out", "lost", "unavailable"]
Guard = Callable[[], SendStatus | None]
_LOG = logging.getLogger(__name__)


def text_content(text: str) -> str:
    return json.dumps({"text": text}, ensure_ascii=False, separators=(",", ":"))


def _plain(text: str) -> str:
    # Text messages still interpret at tags. Keep untrusted prose as visible text.
    table: dict[str, str | int | None] = {"<": "＜", ">": "＞", "&": "＆"}
    return text.translate(str.maketrans(table))


def _safe_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        url = urlsplit(value)
        if (
            url.scheme in {"http", "https"}
            and url.hostname
            and not (url.username or url.password or any(c.isspace() for c in value))
        ):
            return value
    except ValueError:
        pass
    return None


def render_answer(answer: ResearchAnswer) -> str:
    """Keep complete claims/citations or replace the entire result; never slice evidence."""
    answer = ResearchAnswer.model_validate(answer)
    lines = (
        [DISCLAIMER]
        if answer.retrieval_scope == "local"
        else [
            "本次使用在线 PubMed"
            + ("及本地来源" if answer.retrieval_scope == "hybrid" else "")
            + "；仅用于科研辅助，不保证检全，不用于个体诊断或治疗决策。"
        ]
    )
    if answer.status == "needs_clarification":
        lines = ["本次尚未执行检索；需先确认关键研究主题或约束。"]
    elif answer.retrieval_scope == "local":
        lines.append("来源范围：local（仅本地；未执行在线 PubMed 检索）。")
    if answer.retrieval_scope != "online":
        lines.append(
            f"本地检索：{answer.local_retrieval_mode}；策略：{answer.local_retrieval_strategy}"
        )
    if answer.search_provenance is not None:
        search = answer.search_provenance
        lines.append(
            f"检索：{_plain(search.query_sent)}；时间：{search.fetched_at.isoformat()}；"
            f"状态：{search.status}；返回 {search.returned_count}/{search.total_count}；"
            f"截断：{search.truncated}"
        )
    numbers = {
        evidence.chunk_id: number
        for number, source in enumerate(answer.sources, 1)
        for evidence in source.evidence
    }
    kinds = {"evidence": "证据", "inference": "推断", "uncertainty": "不确定"}
    scopes = {
        "abstract": "摘要（未阅读全文）",
        "extracted_text": "PDF文本层（完整性未验证）",
        "full_text": "全文来源",
    }
    if answer.query_plan is not None:
        structured = answer.query_plan.structured_question
        lines.append(f"问题分类：{structured.question_type}")
        if answer.status == "needs_clarification":
            lines.append("需澄清：请补充以下信息后重新提问。")
        for label, pico_value in [
            ("P 人群", structured.pico.population),
            ("I 干预/检测", structured.pico.intervention),
            ("C 对照", structured.pico.comparison),
            ("O 结局", structured.pico.outcome),
        ]:
            lines.append(f"{label}：{_plain(pico_value.text) if pico_value else '未提供'}")
        for term in answer.query_plan.terms:
            if term.origin == "query_expansion":
                lines.append(f"候选检索扩展：{_plain(term.text)}")
        questions = structured.blocking_ambiguities or structured.ambiguities
        label = "需澄清" if answer.status == "needs_clarification" else "可选细化"
        lines.extend(f"{label}：{_plain(item)}" for item in questions[:2])
    if answer.status == "insufficient_evidence":
        lines.append("证据不足：未检索到符合条件的证据，不代表证据证明无效。")
    for claim in answer.claims:
        refs = " ".join(f"[{numbers[key]}] chunk={key}" for key in claim.evidence_chunk_ids)
        lines.append(f"{claim.claim_id} {kinds[claim.kind]}：{_plain(claim.text)}\n来源：{refs}")
        lines.extend(f"结论局限：{_plain(item)}" for item in claim.limitations)
    for number, source in enumerate(answer.sources, 1):
        date = source.publication_date
        date_text = date.raw or "未知"
        lines.append(f"[{number}] {_plain(source.title)}")
        lines.append(
            f"作者：{_plain('、'.join(source.authors)) or '未知'}；日期：{_plain(date_text)}；"
            f"期刊：{_plain(source.journal or '未知')}"
        )
        lines.append(
            f"document={source.document_id}；hash={source.content_hash}；"
            f"范围：{scopes[source.content_scope]}"
        )
        for label, value in [
            ("PMID", source.pmid),
            ("DOI", source.doi),
            ("URL", _safe_url(source.source_url)),
        ]:
            if value:
                lines.append(f"{label}：{_plain(value)}")
        if source.publication_types:
            lines.append("出版类型：" + _plain("、".join(source.publication_types)))
        if source.source_notices:
            lines.append("来源关联标记：" + _plain("、".join(source.source_notices)))
        for evidence in source.evidence:
            loc = evidence.location
            position = f"第{loc.page}页" if loc.kind == "pdf_page" else "摘要"
            section = f" {_plain(loc.section)}" if loc.section else ""
            lines.append(f"chunk={evidence.chunk_id} {position}{section} [{loc.start},{loc.end})")
    lines.extend(f"局限：{_plain(item)}" for item in answer.limitations)
    text = "\n".join(lines)
    content = text_content(text)
    # content is itself a JSON string in the outer request. Quotes/backslashes
    # expand twice; reserve the maximum validated chat ID for the create route.
    body = json.dumps(
        {"msg_type": "text", "content": content, "receive_id": "x" * 256},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return (
        text
        if len(content.encode("utf-8")) <= MAX_CONTENT_BYTES and len(body) <= MAX_BODY_BYTES
        else (
            TOO_LONG
            if answer.retrieval_scope == "local"
            else "结果过长，未展示结论及引用。请缩小范围后重试；本次已按记录查询 PubMed。"
        )
    )


def split_report_text(text: str) -> list[str]:
    """Preserve every character, escape Feishu mentions, bound all parts before sending."""
    text = _plain(text)
    # 2000 codepoints bounds worst-case 4-byte Unicode and JSON escaping twice.
    parts = [text[i : i + 2000] for i in range(0, len(text), 2000)] or [""]
    if len(parts) > 32:
        raise ValueError("Report exceeds bounded message count; use CLI/API export")
    return [f"科研调研报告（{i}/{len(parts)}）\n{part}" for i, part in enumerate(parts, 1)]


class SenderPolicy(DTO):
    capacity: Annotated[StrictInt, Field(ge=1, le=64)] = 8
    send_ms: Annotated[StrictInt, Field(ge=1, le=10000)] = 5000
    notice_ms: Annotated[StrictInt, Field(ge=1, le=15000)] = 5000


class SendingDedupPort(Protocol):
    def check(self, lease: Lease) -> OperationResult: ...
    def complete(self, lease: Lease) -> OperationResult: ...
    def release(self, lease: Lease) -> OperationResult: ...


class MessageTransport(Protocol):
    """Call guard immediately before side effects, obey deadline, never retry."""

    def send(
        self, envelope: MessageEnvelope, text: str, *, deadline: float, guard: Guard
    ) -> SendStatus: ...


class OfficialMessageAPI:
    """Borrows a nonretrying HTTP client and a deadline-aware token provider.

    Construct the client explicitly with HTTPTransport(retries=0), redirects disabled,
    no event hooks that log secrets, and no inherited credentials/default parameters.
    """

    def __init__(
        self,
        client: "httpx.Client",
        *,
        token: Callable[[float], str],
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._client, self._token, self._clock = client, token, clock

    def send(
        self, envelope: MessageEnvelope, text: str, *, deadline: float, guard: Guard
    ) -> SendStatus:
        # No message call has started in this stage: failure is definitely unsent.
        if self._clock() >= deadline:
            return "timed_out"
        try:
            token = self._token(deadline)
            if not isinstance(token, str) or not token.strip() or any(c.isspace() for c in token):
                return "failed"
            content = text_content(text)
            if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
                return "failed"
            body = {"msg_type": "text", "content": content}
            path, params = "/im/v1/messages", {}
            if envelope.message_id:
                path += f"/{envelope.message_id}/reply"
            else:
                body["receive_id"] = envelope.chat_id
                params["receive_id_type"] = "chat_id"
            payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if len(payload) > MAX_BODY_BYTES:
                return "failed"
            stopped = guard()
            if stopped:
                return stopped
            remaining = deadline - self._clock()
            if remaining <= 0:
                return "timed_out"
        except Exception:
            return "failed"
        try:
            response = self._client.post(
                "https://open.feishu.cn/open-apis" + path,
                params=params,
                content=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=remaining,
                follow_redirects=False,
            )
            if 400 <= response.status_code < 500:
                return "failed"
            if not 200 <= response.status_code < 300:
                return "unknown"
            result = response.json()
            if not isinstance(result, dict) or type(result.get("code")) is not int:
                return "unknown"
            if result["code"] != 0:
                return "failed"
            data = result.get("data")
            if (
                isinstance(data, dict)
                and isinstance(data.get("message_id"), str)
                and data["message_id"].strip()
            ):
                return "sent"
        except Exception:
            # An exception after starting HTTP cannot prove absence of a side effect.
            pass
        return "unknown"


@dataclass(frozen=True)
class _Item:
    envelope: MessageEnvelope
    deadline: float
    lease: Lease | None = None
    answer: ResearchAnswer | ResearchReport | None = None
    code: NoticeCode | None = None


class Sender:
    """offer transfers leases only on True; close never closes borrowed clients."""

    def __init__(
        self,
        *,
        dedup: SendingDedupPort,
        transport: MessageTransport,
        policy: SenderPolicy | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.policy = SenderPolicy.model_validate(policy if policy is not None else SenderPolicy())
        self._dedup, self._transport, self._clock = dedup, transport, clock
        self._queue: Queue[_Item] = Queue(maxsize=self.policy.capacity)
        self._lock = RLock()
        self._pending = 0
        self._closing = False
        self._thread = Thread(target=self._run, name="clinical-feishu-sender")
        self._thread.start()

    def _offer(self, item: _Item) -> bool:
        with self._lock:
            if self._closing or self._pending >= self.policy.capacity:
                return False
            self._queue.put_nowait(item)
            self._pending += 1
            return True

    def offer(self, delivery: Delivery) -> bool:
        try:
            envelope = MessageEnvelope.model_validate(delivery.envelope).model_copy(deep=True)
            lease = Lease.model_validate(delivery.lease).model_copy(deep=True)
            deadline = delivery.deadline
            if (
                isinstance(deadline, bool)
                or not isinstance(deadline, (int, float))
                or not isfinite(deadline)
            ):
                raise ValueError
            if lease.identity != envelope.dedup_identity:
                raise ValueError
            if (delivery.answer is None) == (delivery.error_code is None):
                raise ValueError
            answer = None
            if delivery.answer is not None:
                answer = (
                    ResearchReport.model_validate(delivery.answer)
                    if isinstance(delivery.answer, ResearchReport)
                    else ResearchAnswer.model_validate(delivery.answer)
                ).model_copy(deep=True)
                if answer.request_id != envelope.request_id:
                    raise ValueError
            elif delivery.error_code != "research_failed":
                raise ValueError
            item = _Item(envelope, deadline, lease, answer, delivery.error_code)
        except Exception:
            raise ValueError("Invalid delivery") from None
        return self._offer(item)

    def offer_notice(self, envelope: MessageEnvelope, code: NoticeCode) -> bool:
        if code not in NOTICE:
            raise ValueError("Invalid notice")
        envelope = MessageEnvelope.model_validate(envelope).model_copy(deep=True)
        return self._offer(_Item(envelope, self._clock() + self.policy.notice_ms / 1000, code=code))

    def _guard(self, item: _Item) -> SendStatus | None:
        if self._clock() >= item.deadline:
            return "timed_out"
        if item.lease is not None:
            try:
                state = self._dedup.check(item.lease)
            except Exception:
                return "unavailable"
            if state != "owned":
                return "lost" if state == "lost" else "unavailable"
        return "timed_out" if self._clock() >= item.deadline else None

    def _process(self, item: _Item) -> None:
        status = self._guard(item)
        if status is None:
            try:
                text = (
                    (
                        render_report(item.answer)
                        if isinstance(item.answer, ResearchReport)
                        else render_answer(item.answer)
                    )
                    if item.answer is not None
                    else NOTICE[item.code or "research_failed"]
                )
            except Exception:
                text = NOTICE["research_failed"]
            status = self._guard(item)
            if status is None:
                try:
                    try:
                        parts = (
                            split_report_text(text)
                            if isinstance(item.answer, ResearchReport)
                            else [text]
                        )
                    except ValueError:
                        parts = [
                            "报告过长，未发送任何报告内容或引用。"
                            "请缩小检索范围，或使用 CLI/API 获取完整报告。"
                        ]
                    for index, part in enumerate(parts):
                        status = (
                            self._guard(item) if isinstance(item.answer, ResearchReport) else None
                        )
                        if status is None:
                            status = self._transport.send(
                                item.envelope,
                                part,
                                deadline=min(
                                    item.deadline, self._clock() + self.policy.send_ms / 1000
                                ),
                                guard=lambda: self._guard(item),
                            )
                        if status != "sent":
                            if index:
                                status = "unknown"
                            break
                    if status not in get_args(SendStatus):
                        status = "unknown"
                except Exception:
                    status = "unknown"
        cleanup = "untouched"
        if item.lease is not None and status in {"sent", "failed", "timed_out"}:
            try:
                operation = self._dedup.complete if status == "sent" else self._dedup.release
                cleanup = operation(item.lease)
                if cleanup not in {"owned", "lost", "unavailable"}:
                    cleanup = "unavailable"
            except Exception:
                cleanup = "unavailable"
        _LOG.info(
            "feishu_delivery",
            extra={
                "request_id": str(item.envelope.request_id),
                "status": status,
                "dedup_status": cleanup,
            },
        )

    def _run(self) -> None:
        while True:
            try:
                item = self._queue.get(timeout=0.05)
            except Empty:
                with self._lock:
                    if self._closing and not self._pending:
                        return
                continue
            try:
                self._process(item)
            finally:
                with self._lock:
                    self._pending -= 1
                self._queue.task_done()

    def close(self, *, timeout_seconds: float = 5.0) -> bool:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not isfinite(timeout_seconds)
            or timeout_seconds < 0
        ):
            raise ValueError("Invalid shutdown timeout")
        with self._lock:
            self._closing = True
        self._thread.join(timeout_seconds)
        return not self._thread.is_alive()
