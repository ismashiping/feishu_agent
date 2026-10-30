"""Explicit operator for the authorized stage-3 deployment; never prints credentials."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/openalex-stage3/deployment"
AUDIT.mkdir(exist_ok=True)


def inspect(name):
    return json.loads(subprocess.check_output(["docker", "inspect", name]))[0]


api = inspect("clinical-agent-e2e-api-1")
bot = inspect("clinical-agent-e2e-feishu_bot-1")
api_env = dict(x.split("=", 1) for x in api["Config"]["Env"] if "=" in x)
bot_env = dict(x.split("=", 1) for x in bot["Config"]["Env"] if "=" in x)
assert api_env["CLINICAL_AGENT_DB_NAME"] == "clinical_agent_e2e"
assert api["Config"]["Labels"]["com.docker.compose.project"] == "clinical-agent-e2e"
environment = dict(os.environ)
for source in (api_env, bot_env):
    for key, value in source.items():
        if key.startswith(("CLINICAL_AGENT_", "LLM_", "OPENALEX_", "PUBMED_")):
            environment[key] = value
# Compose host port is different from the application's internal database port.
pg = inspect("clinical-agent-e2e-postgres-1")
environment["CLINICAL_AGENT_DB_PORT"] = pg["HostConfig"]["PortBindings"]["5432/tcp"][0]["HostPort"]
environment["CLINICAL_AGENT_API_PORT"] = api["HostConfig"]["PortBindings"]["8000/tcp"][0][
    "HostPort"
]
model_source = next(m["Source"] for m in api["Mounts"] if m["Destination"] == "/app/model")
prefix = "/run/desktop/mnt/host/"
if model_source.startswith(prefix):
    model_source = model_source[len(prefix) :]
    model_source = model_source[0].upper() + ":/" + model_source[2:]
environment["CLINICAL_AGENT_MODEL_DIR"] = model_source
compose = ["docker", "compose", "-p", "clinical-agent-e2e", "--profile", "api", "--profile", "bot"]


def run(args):
    subprocess.run(args, cwd=ROOT, env=environment, check=True)


mode = sys.argv[1]
if mode == "build":
    old_image = api["Image"]
    run(["docker", "tag", old_image, "clinical-literature-agent:pre-oa-stage3-20261029"])
    (AUDIT / "before.json").write_text(
        json.dumps(
            {"old_image": old_image, "database": api_env["CLINICAL_AGENT_DB_NAME"]}, indent=2
        )
    )
    run(compose + ["build", "api"])
elif mode == "migrate":
    run(compose + ["stop", "api", "feishu_bot"])
    backup = ROOT / "data/deployment-backups/oa-stage3-20261029.dump"
    backup.parent.mkdir(parents=True, exist_ok=True)
    assert not backup.exists(), "Do not overwrite a previous business backup"
    run(
        [
            "docker",
            "exec",
            "clinical-agent-e2e-postgres-1",
            "pg_dump",
            "-U",
            "clinical_agent",
            "-d",
            "clinical_agent_e2e",
            "-Fc",
            "-f",
            "/tmp/oa-stage3-20261029.dump",
        ]
    )
    run(["docker", "cp", "clinical-agent-e2e-postgres-1:/tmp/oa-stage3-20261029.dump", str(backup)])
    run(
        [
            "docker",
            "exec",
            "clinical-agent-e2e-postgres-1",
            "pg_restore",
            "--list",
            "/tmp/oa-stage3-20261029.dump",
        ]
    )
    (AUDIT / "backup.json").write_text(
        json.dumps(
            {
                "path": str(backup.relative_to(ROOT)),
                "bytes": backup.stat().st_size,
                "sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )
    run(compose + ["run", "--rm", "--no-deps", "api", "alembic", "upgrade", "head"])
elif mode == "recreate":
    run(compose + ["up", "-d", "--no-deps", "--force-recreate", "api", "feishu_bot"])
else:
    raise ValueError("Use build, migrate, or recreate")
