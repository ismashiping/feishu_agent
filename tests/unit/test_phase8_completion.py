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


@pytest.mark.parametrize(
    "status,expected",
    [("retracted", 0), ("withdrawn", 0), ("expression_of_concern", 0), ("corrected", 1)],
)
def test_known_governance_applies_to_online_copies(status, expected):
    from datetime import UTC, datetime
    from uuid import uuid4

    from clinical_agent.adapters.pubmed_xml import parse_pubmed_response
    from clinical_agent.application.pubmed import PubMedRetrievalService
    from clinical_agent.domain.governance import EvidenceBasis, GovernanceState
    from clinical_agent.domain.pubmed import PubMedSearchResult
    from clinical_agent.domain.retrieval import RetrievalRequest

    body = (
        b"<PubmedArticleSet>"
        b"<PubmedArticle>"
        b"<MedlineCitation>"
        b"<PMID>123</PMID>"
        b"<Article>"
        b"<ArticleTitle>Fixture</ArticleTitle>"
        b"<Abstract>"
        b"<AbstractText>Evidence.</AbstractText>"
        b"</Abstract>"
        b"</Article>"
        b"</MedlineCitation>"
        b"</PubmedArticle>"
        b"</PubmedArticleSet>"
    )
    now = datetime.now(UTC)
    records = parse_pubmed_response(body, fetched_at=now)
    state = GovernanceState(
        status=status,
        event_id=uuid4(),
        evidence=EvidenceBasis(
            uri="https://example.org/notice",
            snapshot_hash="a" * 64,
            quote="Synthetic status",
            recorded_by="test",
        ),
    )

    class Search:
        def search(self, *args, **kwargs):
            return PubMedSearchResult(
                query_sent="q",
                query_translation=None,
                total_count=1,
                requested_limit=10,
                returned_count=1,
                truncated=False,
                fetched_at=now,
                date_from=None,
                date_to=None,
                date_field="pdat",
                sort="relevance",
                status="complete",
                warnings=[],
                missing_pmids=[],
                records=records,
            )

    class Lookup:
        def statuses_for_pmids(self, ids):
            assert ids == ["123"]
            return {"123": state}

    result = PubMedRetrievalService(Search(), governance=Lookup()).retrieve(
        RetrievalRequest(question="q", scope="online")
    )
    assert len(result.hits) == expected
    assert "source_governance_known_pmids" in result.warnings
    if expected:
        assert result.hits[0].document.governance == state


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
