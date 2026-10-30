"""Provider-independent generation through LangChain's standard chat model API."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from time import monotonic
from typing import TYPE_CHECKING

from clinical_agent.domain.pico import PICO_INSTRUCTIONS, ClassificationRequest, ExtractionDraft
from clinical_agent.domain.research import GenerationInput, ResearchError

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


def _metric(value: object) -> str:
    if isinstance(value, str) and value.isdigit() and len(value) <= 7:
        return value
    if type(value) is int and 0 <= value <= 1_000_000:
        return str(value)
    return "unknown"


def _completion_details(message: object) -> dict[str, str]:
    content = getattr(message, "content", None)
    chars = str(len(content.encode("utf-8"))) if isinstance(content, str) else "unknown"
    meta = getattr(message, "response_metadata", None)
    finish = "unknown"
    usage: object = None
    if isinstance(meta, dict):
        reason = meta.get("finish_reason")
        if isinstance(reason, str) and reason.isascii() and reason.replace("_", "").isalnum():
            lowered = reason.lower()
            if lowered[:1].islower() and lowered.replace("_", "").isalnum() and len(lowered) <= 40:
                finish = lowered
        usage = meta.get("token_usage")
        if not isinstance(usage, dict):
            usage = meta.get("usage")
    details = usage.get("completion_tokens_details") if isinstance(usage, dict) else None
    reasoning: object = "unknown"
    if isinstance(details, dict) and "reasoning_tokens" in details:
        reasoning = details.get("reasoning_tokens")
    return {
        "finish_reason": finish,
        "content_chars": chars if chars == "unknown" or chars.isdigit() else "unknown",
        "input_tokens": _metric(usage.get("prompt_tokens") if isinstance(usage, dict) else None),
        "output_tokens": _metric(
            usage.get("completion_tokens") if isinstance(usage, dict) else None
        ),
        "reasoning_tokens": _metric(reasoning),
    }


class LangChainAnswerGenerator:
    def __init__(self, model: BaseChatModel) -> None:
        self._model = model
        self.completion_details: dict[str, str] = {}

    def generate(self, context: GenerationInput, *, timeout_seconds: float) -> str:
        context = GenerationInput.model_validate(context)
        return self._invoke(
            context.instructions, context.model_dump_json(exclude={"instructions"}), timeout_seconds
        )

    def extract(self, request: ClassificationRequest, *, timeout_seconds: float) -> str:
        request = ClassificationRequest.model_validate(request)
        schema = deepcopy(ExtractionDraft.model_json_schema())
        required = list(schema.get("required", []))
        if "task_intent" not in required:
            required.append("task_intent")
        schema["required"] = required
        payload = json.dumps(
            {
                **request.model_dump(),
                "question_codepoints": list(enumerate(request.question))
                if len(request.question) <= 256
                else None,
                "output_schema": schema,
            },
            ensure_ascii=False,
        )
        return self._invoke(PICO_INSTRUCTIONS, payload, timeout_seconds, disable_thinking=True)

    def analyze_evidence(
        self,
        context: dict[str, object],
        *,
        timeout_seconds: float,
        max_output_tokens: int | None = None,
    ) -> str:
        from clinical_agent.domain.analysis import ANALYSIS_INSTRUCTIONS

        return self._invoke(
            ANALYSIS_INSTRUCTIONS,
            json.dumps(context, ensure_ascii=False),
            timeout_seconds,
            disable_thinking=True,
            max_output_tokens=max_output_tokens,
        )

    def screen_candidates(self, context: dict[str, object], *, timeout_seconds: float) -> str:
        from clinical_agent.domain.openalex import SCREENING_INSTRUCTIONS

        return self._invoke(
            SCREENING_INSTRUCTIONS,
            json.dumps(context, ensure_ascii=False),
            timeout_seconds,
            disable_thinking=True,
        )

    def review_claims(self, context: dict[str, object], *, timeout_seconds: float) -> str:
        from clinical_agent.domain.report import REVIEW_INSTRUCTIONS

        return self._invoke(
            REVIEW_INSTRUCTIONS, json.dumps(context, ensure_ascii=False), timeout_seconds
        )

    def _invoke(
        self,
        instructions: str,
        payload: str,
        timeout_seconds: float,
        *,
        disable_thinking: bool = False,
        max_output_tokens: int | None = None,
    ) -> str:
        import httpx
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        from langsmith import tracing_context

        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ResearchError("generation_timeout")
        self.completion_details = {}
        deadline = monotonic() + timeout_seconds
        request_kwargs: dict[str, object] = {}
        if disable_thinking or max_output_tokens is not None:
            # Provider thinking is on by default and can consume the whole output budget,
            # leaving content empty. Structured JSON calls need that content.
            body = dict(getattr(self._model, "extra_body", None) or {})
            if disable_thinking:
                body["thinking"] = {"type": "disabled"}
            if max_output_tokens is not None:
                body["max_tokens"] = max_output_tokens
            request_kwargs["extra_body"] = body
        try:
            with tracing_context(enabled=False):
                message = self._model.invoke(
                    [
                        SystemMessage(content=instructions),
                        HumanMessage(content=payload),
                    ],
                    config={"callbacks": []},
                    response_format={"type": "json_object"},
                    **request_kwargs,
                    timeout=httpx.Timeout(
                        timeout_seconds,
                        connect=min(5.0, timeout_seconds),
                        write=min(5.0, timeout_seconds),
                        pool=min(5.0, timeout_seconds),
                    ),
                )
            if monotonic() >= deadline:
                raise ResearchError("generation_timeout")
            self.completion_details = _completion_details(message)
            if (
                not isinstance(message, AIMessage)
                or message.tool_calls
                or message.invalid_tool_calls
                or message.additional_kwargs.get("tool_calls")
                or message.response_metadata.get("finish_reason", "stop") != "stop"
                or not isinstance(message.content, str)
                or not message.content.strip()
                or len(message.content.encode("utf-8")) > 128000
            ):
                _log_rejected_output(message)
                raise ResearchError("model_output_invalid", details=self.completion_details)
            return message.content
        except Exception as error:
            # Provider SDKs may wrap transport errors; preserve our bounded HTTP errors.
            cause: BaseException | None = error
            seen: set[int] = set()
            while cause is not None and id(cause) not in seen:
                seen.add(id(cause))
                if isinstance(cause, ResearchError):
                    raise ResearchError(cause.code, details=cause.details) from None
                if isinstance(cause, (httpx.TimeoutException, TimeoutError)):
                    raise ResearchError("generation_timeout") from None
                cause = cause.__cause__
            raise ResearchError("generation_failed") from None


def _log_rejected_output(message: object) -> None:
    from clinical_agent.application.openalex import log_evidence_trace

    content = getattr(message, "content", None)
    chars = len(content.encode("utf-8")) if isinstance(content, str) else 0
    meta = getattr(message, "response_metadata", None)
    usage = meta.get("token_usage") if isinstance(meta, dict) else None
    if not isinstance(usage, dict) and isinstance(meta, dict):
        usage = meta.get("usage")
    details = usage.get("completion_tokens_details") if isinstance(usage, dict) else None
    if isinstance(details, dict) and "reasoning_tokens" in details:
        reasoning: int | str = details.get("reasoning_tokens")
        if type(reasoning) is not int or not 0 <= reasoning <= 1_000_000:
            reasoning = "unknown"
    else:
        reasoning = "unknown"
    finish = meta.get("finish_reason") if isinstance(meta, dict) else None
    kind = finish if isinstance(finish, str) else "model_output_invalid"
    log_evidence_trace(
        stage="provider",
        counts={"content_chars": chars, "reasoning_tokens": reasoning},
        failure_kind=kind,
    )
