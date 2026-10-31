"""Observe API lifespan using injected services and in-process HTTP only."""
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from clinical_agent.api import create_app
from clinical_agent.api.runtime import ServiceBundle
from clinical_agent.api.schemas import ApiSettings


def main():
    events = []

    @contextmanager
    def factory(settings):
        events.append("enter")
        try:
            yield ServiceBundle(ingestion=object(), research=object())
        finally:
            events.append("exit")

    with TemporaryDirectory() as folder:
        root = Path(folder)
        settings = ApiSettings(model_dir=root, import_root=root, snapshot_dir=root)
        app = create_app(settings=settings, runtime_factory=factory)
        assert events == []
        with TestClient(app) as client:
            response = client.get("/health/ready")
            assert response.status_code == 200
            assert response.json()["request_id"] == response.headers["x-request-id"]
            print("inside:", events, response.json()["status"])
        assert events == ["enter", "exit"]
        print("after:", events)


if __name__ == "__main__":
    main()
