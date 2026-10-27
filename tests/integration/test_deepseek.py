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
    from clinical_agent.adapters.deepseek import DeepSeekSettings

    data = dict(api_key="synthetic-secret", base_url="https://api.deepseek.com", model="test-model")
    data.update(changes)
    return DeepSeekSettings(**data)


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
        "http://api.deepseek.com",
        "https://evil.test",
        "https://api.deepseek.com@evil.test",
        "https://api.deepseek.com/other",
    ],
)
def test_credentials_only_go_to_explicit_official_origin(url):
    with pytest.raises(ValidationError) as error:
        settings(base_url=url)
    assert "synthetic-secret" not in str(error.value)


def test_settings_are_explicit_secret_and_environment_only(monkeypatch, tmp_path):
    from clinical_agent.adapters.deepseek import DeepSeekSettings

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=file-secret\nDEEPSEEK_MODEL=file-model")
    for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValidationError):
        DeepSeekSettings()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-secret")
    monkeypatch.setenv("DEEPSEEK_MODEL", "explicit-model")
    value = DeepSeekSettings()
    assert value.model == "explicit-model"
    assert "env-secret" not in repr(value)
    assert "env-secret" not in value.model_dump_json()


def test_official_protocol_timeout_and_lifecycle():
    from clinical_agent.adapters.deepseek import deepseek_generator

    seen = []

    def handler(request):
        seen.append(request)
        payload = json.loads(request.content)
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["Authorization"] == "Bearer synthetic-secret"
        assert payload["model"] == "test-model" and payload["stream"] is False
        assert payload["response_format"] == {"type": "json_object"}
        assert "tools" not in payload and payload["max_tokens"] == 1500
        assert payload["messages"][0]["role"] == "system"
        assert "json" in payload["messages"][0]["content"].lower()
        assert "source_uri" not in request.content.decode()
        assert 0 < request.extensions["timeout"]["read"] <= 2.0
        return httpx.Response(200, json=envelope())

    with deepseek_generator(settings(), transport=httpx.MockTransport(handler)) as generator:
        assert generator.generate(context(), timeout_seconds=2.0) == '{"claims":[]}'
        client = generator._client
        assert not client.is_closed
    assert client.is_closed and len(seen) == 1


@pytest.mark.parametrize("status", [301, 401, 429, 500])
def test_http_failures_no_retry_or_body_leak(status):
    from clinical_agent.adapters.deepseek import deepseek_generator
    from clinical_agent.domain.research import ResearchError

    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status, text="synthetic-secret private-body", headers={"Location": "https://evil.test"}
        )

    with deepseek_generator(settings(), transport=httpx.MockTransport(handler)) as generator:
        with pytest.raises(ResearchError, match="generation_failed") as error:
            generator.generate(context(), timeout_seconds=2.0)
    assert str(error.value) == "generation_failed" and len(calls) == 1


@pytest.mark.parametrize(
    "failure,code",
    [(httpx.ReadTimeout, "generation_timeout"), (httpx.ConnectError, "generation_failed")],
)
def test_transport_failures_are_controlled(failure, code):
    from clinical_agent.adapters.deepseek import deepseek_generator
    from clinical_agent.domain.research import ResearchError

    def handler(request):
        raise failure("private upstream", request=request)

    with deepseek_generator(settings(), transport=httpx.MockTransport(handler)) as generator:
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
    from clinical_agent.adapters.deepseek import deepseek_generator
    from clinical_agent.domain.research import ResearchError

    with deepseek_generator(
        settings(),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=envelope(**change))),
    ) as generator:
        with pytest.raises(ResearchError, match="model_output_invalid"):
            generator.generate(context(), timeout_seconds=2.0)


def test_response_stream_is_bounded_and_closed():
    from clinical_agent.adapters.deepseek import deepseek_generator
    from clinical_agent.domain.research import ResearchError

    class Huge(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            yield b" " * 128001
            raise AssertionError("Should stop before consuming more data")

        def close(self):
            self.closed = True

    stream = Huge()
    with deepseek_generator(
        settings(),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=stream)),
    ) as generator:
        with pytest.raises(ResearchError, match="model_output_invalid"):
            generator.generate(context(), timeout_seconds=2.0)
    assert stream.closed


def test_mutated_settings_revalidated_before_creating_client():
    from clinical_agent.adapters.deepseek import deepseek_generator

    config = settings()
    config.base_url = "https://evil.test"
    with pytest.raises(ValidationError):
        with deepseek_generator(config):
            raise AssertionError("Unvalidated endpoint must never be assembled")
