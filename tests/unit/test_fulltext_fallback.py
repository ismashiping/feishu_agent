"""Deterministic HTTP candidate fallback and shared budget regression."""

import logging

import httpx
import pytest

from clinical_agent.integrations import oa_fulltext as oa
from tests.unit.test_oa_fulltext import _nnunet, _pdf, _source


@pytest.mark.parametrize("failure", ["timeout", "size", "format"])
def test_candidate_failure_falls_back(tmp_path, monkeypatch, caplog, failure):
    monkeypatch.setattr(oa, "monotonic", lambda: 10.0)
    selected = _nnunet(content_urls={"pdf": "https://content.openalex.org/first.pdf"})
    body = _pdf(tmp_path, selected.title, selected.doi)
    seen = []
    responses = []

    def handler(request):
        seen.append(request.url.path)
        if len(seen) == 1:
            if failure == "timeout":
                raise httpx.ReadTimeout("private-token", request=request)
            response = httpx.Response(
                200, content=b"x" * (10 * 1024 * 1024 + 1) if failure == "size" else b"invalid"
            )
        else:
            response = httpx.Response(200, content=body)
        responses.append(response)
        return response

    count = [0]
    with (
        caplog.at_level(logging.INFO),
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
    ):
        result = _source(client).fetch_record(selected, 40.0, count)
    assert result.units
    assert len(seen) == 2 and count == [2]
    assert all(r.is_closed for r in responses)
    assert "private-token" not in caplog.text


@pytest.mark.parametrize("limit", ["requests", "deadline"])
def test_global_budget_stops_candidates(monkeypatch, limit):
    now = [10.0]
    monkeypatch.setattr(oa, "monotonic", lambda: now[0])
    selected = _nnunet(content_urls={"pdf": "https://content.openalex.org/first.pdf"})
    count = [oa.HTTP_LIMIT - 1] if limit == "requests" else [0]
    seen = []

    def handler(request):
        seen.append(request.url.path)
        if limit == "deadline":
            now[0] = 40.0
        raise httpx.ReadTimeout("timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(oa.AcquisitionError, match="fulltext_budget") as caught:
            _source(client).fetch_record(selected, 40.0, count)
    assert caught.value.basis == ("http_limit" if limit == "requests" else "deadline")
    assert len(seen) == 1


def test_all_timeouts_keep_candidate_failure(monkeypatch):
    monkeypatch.setattr(oa, "monotonic", lambda: 10.0)
    selected = _nnunet(content_urls={"pdf": "https://content.openalex.org/first.pdf"})
    count = [0]

    def handler(request):
        raise httpx.ConnectTimeout("secret", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(oa.AcquisitionError, match="fulltext_timeout") as caught:
            _source(client).fetch_record(selected, 40.0, count)
    assert count == [2]
    assert caught.value.basis == "http_timeout"


@pytest.mark.parametrize("limit", ["requests", "deadline"])
def test_already_exhausted_budget_never_calls_http(monkeypatch, limit):
    monkeypatch.setattr(oa, "monotonic", lambda: 10.0)
    count = [oa.HTTP_LIMIT] if limit == "requests" else [0]
    deadline = 40.0 if limit == "requests" else 10.0
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("HTTP after budget"))
    ) as client:
        with pytest.raises(oa.AcquisitionError, match="fulltext_budget") as caught:
            _source(client).fetch_record(_nnunet(), deadline, count)
    assert caught.value.basis == ("http_limit" if limit == "requests" else "deadline")


def test_stream_deadline_closes_response(monkeypatch):
    now = [10.0]
    monkeypatch.setattr(oa, "monotonic", lambda: now[0])

    class Stream(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            now[0] = 40.0
            yield b"%PDF-content"

        def close(self):
            self.closed = True

    stream = Stream()
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, stream=stream)

    selected = _nnunet(content_urls={"pdf": "https://content.openalex.org/first.pdf"})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(oa.AcquisitionError) as caught:
            _source(client).fetch_record(selected, 40.0, [0])
    assert caught.value.basis == "deadline"
    assert stream.closed and len(seen) == 1
