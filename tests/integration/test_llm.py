"""Real HTTPX transport/protocol, with synthetic remote responses and no network."""

import json

import httpx
import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.integration


def context():
    from clinical_agent.domain.research import GenerationInput

    return GenerationInput(
        question="Synthetic question",
        evidence=[
            {
                "chunk_id": "00000000-0000-0000-0000-000000000001",
                "text": "Synthetic evidence.",
                "content_scope": "abstract",
                "location": {"kind": "abstract", "section": "RESULTS", "start": 0, "end": 19},
            }
        ],
    )


def settings(**changes):
    from clinical_agent.adapters.llm import LLMSettings

    data = dict(
        api_key="synthetic-secret", base_url="https://api.example.test/v1", model="test-model"
    )
    data.update(changes)
    return LLMSettings(**data)


def envelope(**changes):
    result = {
        "model": "test-model",
        "choices": [
            {"finish_reason": "stop", "message": {"role": "assistant", "content": '{"claims":[]}'}}
        ],
    }
    result.update(changes)
    return result


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.test",
        "ftp://api.example.test",
        "https://user:password@api.example.test",
        "https://api.example.test?key=secret",
        "https://api.example.test#fragment",
    ],
)
def test_invalid_endpoint_configuration_is_rejected(url):
    with pytest.raises(ValidationError) as error:
        settings(base_url=url)
    assert "synthetic-secret" not in str(error.value)


def test_settings_are_explicit_secret_and_environment_only(monkeypatch, tmp_path):
    from clinical_agent.adapters.llm import LLMSettings

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("LLM_API_KEY=file-secret\nLLM_MODEL=file-model")
    for key in ("LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValidationError):
        LLMSettings()
    monkeypatch.setenv("LLM_API_KEY", "env-secret")
    monkeypatch.setenv("LLM_MODEL", "explicit-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.test/v1")
    value = LLMSettings()
    assert value.model == "explicit-model"
    assert "env-secret" not in repr(value)
    assert "env-secret" not in value.model_dump_json()


def test_compatible_protocol_timeout_and_lifecycle():
    from clinical_agent.adapters.llm import open_llm

    seen = []

    def handler(request):
        seen.append(request)
        payload = json.loads(request.content)
        assert str(request.url) == "https://api.example.test/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer synthetic-secret"
        assert payload["model"] == "test-model" and payload["stream"] is False
        assert payload["response_format"] == {"type": "json_object"}
        assert "tools" not in payload and payload["max_tokens"] == 1500
        assert payload["messages"][0]["role"] == "system"
        assert "json" in payload["messages"][0]["content"].lower()
        assert "source_uri" not in request.content.decode()
        assert 0 < request.extensions["timeout"]["read"] <= 2.0
        return httpx.Response(200, json=envelope())

    with open_llm(settings(), transport=httpx.MockTransport(handler)) as generator:
        assert generator.generate(context(), timeout_seconds=2.0) == '{"claims":[]}'
        client = generator._model.http_client
        assert not client.is_closed
    assert client.is_closed and len(seen) == 1


@pytest.mark.parametrize("status", [301, 401, 429, 500])
def test_http_failures_no_retry_or_body_leak(status):
    from clinical_agent.adapters.llm import open_llm
    from clinical_agent.domain.research import ResearchError

    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status, text="synthetic-secret private-body", headers={"Location": "https://evil.test"}
        )

    with open_llm(settings(), transport=httpx.MockTransport(handler)) as generator:
        with pytest.raises(ResearchError, match="generation_failed") as error:
            generator.generate(context(), timeout_seconds=2.0)
    assert str(error.value) == "generation_failed" and len(calls) == 1


@pytest.mark.parametrize(
    "failure,code",
    [(httpx.ReadTimeout, "generation_timeout"), (httpx.ConnectError, "generation_failed")],
)
def test_transport_failures_are_controlled(failure, code):
    from clinical_agent.adapters.llm import open_llm
    from clinical_agent.domain.research import ResearchError

    def handler(request):
        raise failure("private upstream", request=request)

    with open_llm(settings(), transport=httpx.MockTransport(handler)) as generator:
        with pytest.raises(ResearchError) as error:
            generator.generate(context(), timeout_seconds=2.0)
    assert str(error.value) == code


@pytest.mark.parametrize(
    "change",
    [
        {"choices": []},
        {"choices": [None]},
        {
            "choices": [
                {"finish_reason": "length", "message": {"role": "assistant", "content": "{}"}}
            ]
        },
        {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": " "}}]},
        {"choices": [{"finish_reason": "stop", "message": {"role": "tool", "content": "{}"}}]},
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "{}", "tool_calls": [{}]},
                }
            ]
        },
    ],
)
def test_malformed_or_truncated_envelope_is_not_an_answer(change):
    from clinical_agent.adapters.llm import open_llm
    from clinical_agent.domain.research import ResearchError

    with open_llm(
        settings(),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=envelope(**change))),
    ) as generator:
        with pytest.raises(ResearchError, match="model_output_invalid"):
            generator.generate(context(), timeout_seconds=2.0)


def test_response_stream_is_bounded_and_closed():
    from clinical_agent.adapters.llm import open_llm
    from clinical_agent.domain.research import ResearchError

    class Huge(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            yield b" " * 128001
            raise AssertionError("Should stop before consuming more data")

        def close(self):
            self.closed = True

    stream = Huge()
    with open_llm(
        settings(),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=stream)),
    ) as generator:
        with pytest.raises(ResearchError, match="model_output_invalid"):
            generator.generate(context(), timeout_seconds=2.0)
    assert stream.closed


def test_mutated_settings_revalidated_before_creating_client():
    from clinical_agent.adapters.llm import open_llm

    config = settings()
    config.base_url = "https://user:password@api.example.test"
    with pytest.raises(ValidationError):
        with open_llm(config):
            raise AssertionError("Unvalidated endpoint must never be assembled")


@pytest.mark.parametrize(
    "base_url,model",
    [
        ("https://first.example.test/v1", "model-a"),
        ("https://second.example.test/gateway/api", "model-b"),
        ("http://127.0.0.1:8080/v1", "local-model"),
    ],
)
def test_switch_endpoint_and_model_using_configuration_only(base_url, model):
    from clinical_agent.adapters.llm import open_llm

    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url) == base_url + "/chat/completions"
        assert json.loads(request.content)["model"] == model
        return httpx.Response(200, json=envelope())

    with open_llm(
        settings(base_url=base_url, model=model), transport=httpx.MockTransport(handler)
    ) as generator:
        assert generator.generate(context(), timeout_seconds=2) == '{"claims":[]}'
    assert len(calls) == 1


def test_missing_base_url_never_falls_back_to_a_vendor(monkeypatch):
    from clinical_agent.adapters.llm import LLMSettings

    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    with pytest.raises(ValidationError):
        LLMSettings(api_key="synthetic-secret", model="test-model")
