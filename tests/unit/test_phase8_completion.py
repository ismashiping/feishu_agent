from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError


def test_online_window_bounds():
    from clinical_agent.domain.maintenance import OnlineUpdateRequest

    for kwargs in (
        {"date_to": date(2026, 12, 1)},
        {"date_to": date(2026, 9, 1)},
        {"batch_id": "../bad"},
    ):
        args = dict(
            batch_id="window",
            query="cohort",
            date_from=date(2026, 10, 1),
            date_to=date(2026, 10, 2),
            staging_root=Path("."),
        )
        args.update(kwargs)
        with pytest.raises(ValidationError):
            OnlineUpdateRequest(**args)


@pytest.mark.parametrize("partial,truncated", [(False, True), (True, False)])
def test_incomplete_online_results_never_freeze_or_publish(tmp_path, partial, truncated):
    from datetime import UTC, datetime

    from clinical_agent.application.online_updates import OnlineUpdateService
    from clinical_agent.domain.maintenance import OnlineUpdateRequest
    from clinical_agent.domain.pubmed import PubMedSearchResult

    class Search:
        def search(self, request, **kwargs):
            return PubMedSearchResult(
                query_sent="cohort",
                query_translation=None,
                total_count=21 if truncated else 0,
                requested_limit=20,
                returned_count=0,
                truncated=truncated,
                fetched_at=datetime.now(UTC),
                date_from=request.options.date_from,
                date_to=request.options.date_to,
                date_field="edat",
                sort="pub_date",
                status="partial" if partial else "complete",
                warnings=[],
                missing_pmids=[],
                records=[],
            )

    class NoWrite:
        def lease(self, request):
            from contextlib import nullcontext

            return nullcontext()

        def load(self, request):
            return None

        def save(self, *args):
            raise AssertionError("No freeze")

    request = OnlineUpdateRequest(
        batch_id="incomplete",
        query="cohort",
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 2),
        staging_root=tmp_path,
    )
    result = OnlineUpdateService(
        search=Search(),
        repository=NoWrite(),
        run_local=lambda *_: pytest.fail("No publication"),
        reader=object(),
    ).run(request)
    assert result["status"] == "window_incomplete"
    assert not list(tmp_path.iterdir())


def test_maintenance_ingestion_can_match_rebuilt_policy(monkeypatch):
    from clinical_agent.command_runtime import IngestionCommand, open_ingestion
    from tests.unit.test_command_runtime import patch_components

    patch_components(monkeypatch)
    with open_ingestion(
        IngestionCommand(
            model_dir=Path("model"), snapshot_dir=Path("snapshots"), chunk_max_tokens=256
        )
    ) as service:
        assert service._policy.max_tokens == 256
    with pytest.raises(ValidationError):
        IngestionCommand(
            model_dir=Path("model"), snapshot_dir=Path("snapshots"), chunk_max_tokens=513
        )


def test_online_snapshot_write_failure_leaves_no_partial_target(tmp_path, monkeypatch):
    import os

    from clinical_agent.application.online_updates import _snapshot_file

    target = tmp_path / "record.xml"
    replace = os.replace

    def fail(*args):
        raise OSError("injected disk failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        _snapshot_file(target, b"<snapshot/>")
    assert not target.exists() and not list(tmp_path.iterdir())
    monkeypatch.setattr(os, "replace", replace)
    _snapshot_file(target, b"<snapshot/>")
    assert target.read_bytes() == b"<snapshot/>"
