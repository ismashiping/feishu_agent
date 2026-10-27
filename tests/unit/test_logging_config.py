"""Exercise real structlog/logging integration in isolated processes."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent

BASE_PROGRAM = """
import logging
import structlog
from clinical_agent.config import Settings
from clinical_agent.logging_config import configure_logging
"""


def _run_logging_program(program: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    allowed_env = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC", "PATHEXT"}
    child_env = {key: value for key, value in os.environ.items() if key.upper() in allowed_env}
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", BASE_PROGRAM + dedent(program)],
        cwd=tmp_path,
        env=child_env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, f"Logging program failed: {result.stdout}\n{result.stderr}"
    assert result.stdout == ""
    return result


def test_json_fields_and_stderr(tmp_path: Path) -> None:
    result = _run_logging_program(
        """
        configure_logging(Settings(app_env="test", log_level="INFO"))
        context = {"request_id": "00000000-0000-4000-8000-000000000001", "app_env": "test"}
        structlog.get_logger("clinical_agent").bind(**context).info(
            "structured_event", timestamp="forged", level="forged"
        )
        logging.getLogger("clinical_agent").warning("stdlib_event", extra=context)
        """,
        tmp_path,
    )
    records = [json.loads(line) for line in result.stderr.splitlines()]
    assert [record["event"] for record in records] == ["structured_event", "stdlib_event"]
    assert [record["level"] for record in records] == ["info", "warning"]
    for record in records:
        assert set(record) == {"event", "level", "timestamp", "request_id", "app_env"}
        assert record["request_id"] == "00000000-0000-4000-8000-000000000001"
        assert record["app_env"] == "test"
        timestamp = datetime.fromisoformat(record["timestamp"])
        assert timestamp.utcoffset() == timedelta(0)


def test_level_filter_and_reconfiguration(tmp_path: Path) -> None:
    result = _run_logging_program(
        """
        import io
        class TrackedHandler(logging.StreamHandler):
            def __init__(self, stream):
                super().__init__(stream)
                self.close_calls = 0
            def close(self):
                self.close_calls += 1
                super().close()

        root_buffer, foreign_buffer = io.StringIO(), io.StringIO()
        root_handler = TrackedHandler(root_buffer)
        root = logging.getLogger()
        root.addHandler(root_handler)
        root.setLevel(logging.DEBUG)
        foreign_handler = TrackedHandler(foreign_buffer)
        foreign = logging.getLogger("unrelated_library")
        foreign.addHandler(foreign_handler)
        foreign.setLevel(logging.ERROR)
        original_root_handlers = tuple(root.handlers)
        original_foreign_handlers = tuple(foreign.handlers)

        settings = Settings(app_env="test", log_level="INFO")
        configure_logging(settings)
        old_logger = structlog.get_logger("clinical_agent").bind(request_id="stable-request")
        configure_logging(settings)
        old_logger.debug("hidden_debug")
        old_logger.info("once")
        configure_logging(Settings(log_level="DEBUG"))
        old_logger.debug("debug_once")
        configure_logging(Settings(log_level="WARNING"))
        logging.getLogger("clinical_agent").info("hidden_info")
        logging.getLogger("clinical_agent").warning("warning_once")

        assert tuple(root.handlers) == original_root_handlers
        assert tuple(foreign.handlers) == original_foreign_handlers
        assert root.level == logging.DEBUG
        assert foreign.level == logging.ERROR
        assert root_handler.close_calls == 0
        assert foreign_handler.close_calls == 0
        assert root_buffer.getvalue() == ""
        root.warning("root_still_works")
        foreign.error("foreign_still_works")
        assert "root_still_works" in root_buffer.getvalue()
        assert "foreign_still_works" in foreign_buffer.getvalue()
        """,
        tmp_path,
    )
    records = [json.loads(line) for line in result.stderr.splitlines()]
    assert [record["event"] for record in records] == ["once", "debug_once", "warning_once"]
    assert [record["level"] for record in records] == ["info", "debug", "warning"]


def test_sensitive_fields_are_not_emitted(tmp_path: Path) -> None:
    result = _run_logging_program(
        """
        configure_logging(Settings(log_level="DEBUG"))
        secret = "LOG_TEST_SECRET_SENTINEL"
        class NeverSerialize:
            def __repr__(self):
                raise AssertionError("Unexpected object representation")
            __str__ = __repr__
            def __structlog__(self):
                raise AssertionError("Unexpected object serialization")

        extras = {
            "api_key": secret, "token": secret, "password": secret,
            "headers": {"Authorization": secret}, "payload": {"nested": [secret]},
            "unknown_object": NeverSerialize(), "request_id": NeverSerialize(),
            "error_code": "upstream_failed", "exception_type": "RuntimeError",
        }
        try:
            raise RuntimeError(secret)
        except RuntimeError:
            structlog.get_logger("clinical_agent").exception(
                "structured_failed", stack_info=True, **extras
            )
            logging.getLogger("clinical_agent").exception(
                "stdlib_failed", extra=extras, stack_info=True
            )
        logging.getLogger("clinical_agent").info("fixed_event", secret)
        """,
        tmp_path,
    )
    assert "LOG_TEST_SECRET_SENTINEL" not in result.stderr
    assert "Traceback" not in result.stderr
    assert "Stack (most recent call last)" not in result.stderr
    records = [json.loads(line) for line in result.stderr.splitlines()]
    assert [record["event"] for record in records] == [
        "structured_failed",
        "stdlib_failed",
        "fixed_event",
    ]
    for record in records[:2]:
        assert set(record) == {"event", "level", "timestamp", "error_code", "exception_type"}
        assert record["error_code"] == "upstream_failed"
        assert record["exception_type"] == "RuntimeError"
        assert record["level"] == "error"
