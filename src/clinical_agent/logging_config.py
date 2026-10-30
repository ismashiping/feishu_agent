"""Explicit JSON logging for the project's named logger."""

import logging
import sys

import structlog
from structlog.typing import EventDict

from clinical_agent.config import Settings

_HANDLER_NAME = "clinical_agent.json"
# Diagnostic values are closed tokens produced by the planner, never payloads.
_CONTEXT_FIELDS = {
    "request_id",
    "app_env",
    "error_code",
    "exception_type",
    "stage",
    "failure_kind",
    "rule_code",
    "field_paths",
    "response_hash",
    "evidence_stage",
    "evidence_counts",
    "model_id",
    "finish_reason",
}
_ALLOWED_FIELDS = _CONTEXT_FIELDS | {"event", "level", "timestamp"}


def _allowed_fields(_logger: object, _method_name: str, event_dict: EventDict) -> EventDict:
    """Exclude extra data and objects before they can be serialized."""
    return {
        key: value
        for key, value in event_dict.items()
        if key in _ALLOWED_FIELDS and isinstance(value, str)
    }


def configure_logging(settings: Settings) -> None:
    """Configure only project handlers, retaining unrelated logging resources."""
    logger = logging.getLogger("clinical_agent")
    for previous in tuple(logger.handlers):
        if previous.get_name() == _HANDLER_NAME:
            logger.removeHandler(previous)
            previous.close()

    handler = logging.StreamHandler(sys.stderr)
    handler.set_name(_HANDLER_NAME)
    handler.setLevel(settings.log_level)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=[structlog.stdlib.ExtraAdder(allow=_CONTEXT_FIELDS)],
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                _allowed_fields,
                structlog.processors.JSONRenderer(ensure_ascii=False),
            ],
            keep_exc_info=False,
            keep_stack_info=False,
            use_get_message=False,
        )
    )
    logger.addHandler(handler)
    logger.setLevel(settings.log_level)
    logger.disabled = False
    logger.propagate = False

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            _allowed_fields,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
