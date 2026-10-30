import pytest


def test_update_request_rejects_escape_and_duplicates(tmp_path):
    from clinical_agent.domain.updates import UpdateRequest

    for paths in [["../bad.pdf"], ["/bad.pdf"], ["a.pdf", "a.pdf"]]:
        with pytest.raises(ValueError):
            UpdateRequest(batch_id="test", allowed_root=tmp_path, files=paths, source_type="pdf")


def test_dry_run_does_not_load_embedder_or_write(tmp_path, pdf_factory):
    from clinical_agent.application.updates import UpdateService
    from clinical_agent.domain.updates import UpdateRequest

    pdf_factory(tmp_path / "a.pdf")

    class Store:
        def load(self, identity):
            return None

    def forbidden(*args):
        raise AssertionError("dry-run must not publish/lock")

    result = UpdateService(ledger=object(), publish=forbidden, reader=Store()).run(
        UpdateRequest(
            batch_id="test", allowed_root=tmp_path, files=["a.pdf"], source_type="pdf", dry_run=True
        )
    )
    assert result.status == "dry_run" and result.cursor_after == result.cursor_before == 0
    assert result.items[0]["status"] == "created"
