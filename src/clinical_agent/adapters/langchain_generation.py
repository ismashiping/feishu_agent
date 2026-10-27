"""Provider-independent generation through LangChain's standard chat model API."""

from __future__ import annotations

import math
from time import monotonic
from typing import TYPE_CHECKING

from clinical_agent.domain.research import GenerationInput, ResearchError

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


class LangChainAnswerGenerator:
    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    def generate(self, context: GenerationInput, *, timeout_seconds: float) -> str:
        import httpx
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        from langsmith import tracing_context

        context = GenerationInput.model_validate(context)
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ResearchError("generation_timeout")
        deadline = monotonic() + timeout_seconds
        try:
            with tracing_context(enabled=False):
                message = self._model.invoke(
                    [
                        SystemMessage(content=context.instructions),
                        HumanMessage(content=context.model_dump_json(exclude={"instructions"})),
                    ],
                    config={"callbacks": []},
                    response_format={"type": "json_object"},
                    timeout=httpx.Timeout(
                        timeout_seconds,
                        connect=min(5.0, timeout_seconds),
                        write=min(5.0, timeout_seconds),
                        pool=min(5.0, timeout_seconds),
                    ),
                )
            if monotonic() >= deadline:
                raise ResearchError("generation_timeout")
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
                raise ResearchError("model_output_invalid")
            return message.content
        except Exception as error:
            # Provider SDKs may wrap transport errors; preserve our bounded HTTP errors.
            cause: BaseException | None = error
            seen: set[int] = set()
            while cause is not None and id(cause) not in seen:
                seen.add(id(cause))
                if isinstance(cause, ResearchError):
                    raise ResearchError(cause.code) from None
                if isinstance(cause, (httpx.TimeoutException, TimeoutError)):
                    raise ResearchError("generation_timeout") from None
                cause = cause.__cause__
            raise ResearchError("generation_failed") from None
