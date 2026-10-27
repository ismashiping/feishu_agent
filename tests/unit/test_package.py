"""Check the installed package from a fresh, isolated Python process."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

IMPORT_AUDIT = r"""
import contextlib
import importlib
import importlib.abc
import io
import json
import logging
import socket
import sys
import threading

import structlog
from pydantic_settings import BaseSettings

attempts = []
blocked_roots = {
    "torch", "transformers", "sentence_transformers", "sqlalchemy",
    "redis", "lark_oapi", "langchain_core", "langchain_openai", "langgraph",
    "langsmith", "httpx", "fastapi", "uvicorn",
}
if sys.argv[1] in {
    "clinical_agent.adapters.postgres.models", "clinical_agent.adapters.postgres.connection",
    "clinical_agent.adapters.postgres.store",
    "clinical_agent.adapters.postgres.retrieval",
}:
    # ORM/engine declarations explicitly depend on SQLAlchemy; all I/O guards still apply.
    blocked_roots.remove("sqlalchemy")

class BlockHeavyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.partition(".")[0] in blocked_roots:
            attempts.append("import:" + fullname)
            raise AssertionError("Heavy dependency imported during package import")
        return None

def forbid(name):
    def guard(*args, **kwargs):
        attempts.append(name)
        raise AssertionError("Resource operation during package import: " + name)
    return guard

sys.meta_path.insert(0, BlockHeavyImports())
socket.create_connection = forbid("socket.create_connection")
socket.getaddrinfo = forbid("socket.getaddrinfo")
socket.socket.connect = forbid("socket.connect")
socket.socket.connect_ex = forbid("socket.connect_ex")
threading.Thread.start = forbid("thread.start")
BaseSettings.__init__ = forbid("settings.construct")
structlog.configure = forbid("logging.configure")

loggers = (logging.getLogger(), logging.getLogger("clinical_agent"))
handlers_before = [tuple(logger.handlers) for logger in loggers]
stdout, stderr = io.StringIO(), io.StringIO()
error = None
module = None
with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
    try:
        module = importlib.import_module(sys.argv[1])
    except Exception as exc:
        error = {"type": type(exc).__name__, "name": getattr(exc, "name", None)}

print(json.dumps({
    "error": error,
    "module_file": getattr(module, "__file__", None),
    "stdout": stdout.getvalue(),
    "stderr": stderr.getvalue(),
    "attempts": attempts,
    "handlers_changed": handlers_before != [tuple(logger.handlers) for logger in loggers],
}))
sys.exit(1 if error else 0)
"""


@pytest.mark.parametrize(
    "module_name",
    [
        "clinical_agent",
        "clinical_agent.config",
        "clinical_agent.logging_config",
        "clinical_agent.bootstrap",
        "clinical_agent.cli",
        "clinical_agent.__main__",
        "clinical_agent.domain",
        "clinical_agent.domain.models",
        "clinical_agent.domain.chunking",
        "clinical_agent.domain.embedding",
        "clinical_agent.adapters",
        "clinical_agent.adapters.pdf",
        "clinical_agent.adapters.pubmed_xml",
        "clinical_agent.adapters.embedding",
        "clinical_agent.adapters.postgres",
        "clinical_agent.adapters.postgres.models",
        "clinical_agent.adapters.postgres.connection",
        "clinical_agent.domain.ingestion",
        "clinical_agent.application",
        "clinical_agent.application.ingestion",
        "clinical_agent.adapters.offline",
        "clinical_agent.adapters.postgres.store",
        "clinical_agent.domain.retrieval",
        "clinical_agent.application.retrieval",
        "clinical_agent.adapters.postgres.retrieval",
        "clinical_agent.domain.research",
        "clinical_agent.domain.citations",
        "clinical_agent.application.research",
        "clinical_agent.adapters.llm",
        "clinical_agent.adapters.langchain_generation",
        "clinical_agent.command_runtime",
        "clinical_agent.api_runtime",
        "clinical_agent.api",
        "feishu",
        "feishu.events",
        "feishu.dedup",
        "feishu.worker",
        "feishu.sender",
        "feishu.main",
    ],
)
def test_package_import_is_isolated_and_quiet(module_name: str, tmp_path: Path) -> None:
    # Keep only OS essentials; neither credentials nor project settings are inherited.
    allowed_env = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC", "PATHEXT"}
    child_env = {key: value for key, value in os.environ.items() if key.upper() in allowed_env}
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", IMPORT_AUDIT, module_name],
        cwd=tmp_path,
        env=child_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, f"Isolated import failed: {result.stdout}\n{result.stderr}"
    report = json.loads(result.stdout)
    assert report["error"] is None
    assert report["stdout"] == ""
    assert report["stderr"] == ""
    assert result.stderr == ""
    assert report["attempts"] == []
    assert report["handlers_changed"] is False
    source_package = Path(__file__).resolve().parents[2] / "src" / module_name.split(".")[0]
    assert Path(report["module_file"]).resolve().is_relative_to(source_package)
