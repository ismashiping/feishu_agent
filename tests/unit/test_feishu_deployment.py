"""Deployment contract checks without credentials or starting real services."""

from pathlib import Path


def test_shared_image_and_explicit_bot_profile():
    root = Path(__file__).resolve().parents[2]
    text = (root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "  feishu_bot:" in text
    assert "  api:" in text
    assert "  redis:" in text
    assert "profiles: [bot]" in text
    assert 'command: ["python", "-m", "feishu.main"]' in text
    assert text.count("image: clinical-literature-agent:local") == 2
    assert "condition: service_healthy" in text
    assert ":/app/model:ro" in text
    assert "127.0.0.1:" in text


def test_image_lock_nonroot_and_build_context():
    root = Path(__file__).resolve().parents[2]
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    assert "uv sync --frozen --no-dev --no-editable" in dockerfile
    assert "--extra feishu" in dockerfile and "--extra ml" in dockerfile
    assert "USER agent" in dockerfile
    assert "COPY . " not in dockerfile
    ignore = (root / ".dockerignore").read_text(encoding="utf-8")
    assert ignore.startswith("*\n")
    assert "!.env" not in ignore and "!models" not in ignore


def test_python_security_patch_matches_shared_image():
    root = Path(__file__).resolve().parents[2]
    version = (root / ".python-version").read_text(encoding="utf-8").strip()
    assert version == "3.12.16"
    assert (
        (root / "Dockerfile")
        .read_text(encoding="utf-8")
        .startswith(f"FROM python:{version}-slim-bookworm")
    )
