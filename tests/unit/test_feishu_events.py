"""Synthetic decoded Feishu events; no SDK, Redis, RAG or network."""

import json
from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError


def payload(text="问题 α🙂\n证据", **message):
    return {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1", "app_id": "cli_test", "event_id": "ev_1"},
        "event": {
            "sender": {"sender_type": "user", "sender_id": {"open_id": "ou_user"}},
            "message": {
                "message_id": "om_1",
                "chat_id": "oc_1",
                "chat_type": "p2p",
                "message_type": "text",
                "content": json.dumps({"text": text}),
                **message,
            },
        },
    }


def decide(data):
    from feishu.events import EventPolicy, filter_event

    return filter_event(data, policy=EventPolicy(app_id="cli_test", bot_open_id="ou_bot"))


def set_path(data, path, value):
    target = data
    parts = path.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value


def mention(key="@_user_1", open_id="ou_bot"):
    return {"key": key, "id": {"open_id": open_id}, "name": "Synthetic"}


def test_normal_message_is_pure_stable_and_compatible_with_question():
    from clinical_agent.domain.research import QuestionRequest

    data = payload("  问题 α🙂\n证据  ")
    data["header"]["token"] = "synthetic-token"
    data["event"]["message"]["future_extension"] = {}
    before = deepcopy(data)
    result = decide(data)
    assert result.status == "accepted" and result.reason == "eligible"
    msg = result.envelope
    assert msg.text == "问题 α🙂\n证据"
    assert msg.sender_id == "ou_user" and msg.sender_type == "user"
    assert msg.chat_id == "oc_1" and msg.chat_type == "p2p" and msg.message_type == "text"
    assert msg.dedup_identity == ("cli_test", "message", "om_1")
    assert isinstance(msg.request_id, UUID)
    assert decide(data) == result
    assert data == before
    assert QuestionRequest(question=msg.text, request_id=msg.request_id).question == msg.text
    assert "synthetic-token" not in result.model_dump_json()


@pytest.mark.parametrize("value", [None, "", " \t"])
def test_event_id_fallback(value):
    msg = decide(payload(message_id=value)).envelope
    assert msg.message_id is None
    assert msg.dedup_identity == ("cli_test", "event", "ev_1")


def test_missing_message_id_fallback_and_optional_event_id():
    data = payload()
    del data["event"]["message"]["message_id"]
    assert decide(data).envelope.dedup_identity[1] == "event"
    data = payload()
    del data["header"]["event_id"]
    assert decide(data).envelope.event_id is None


def test_identity_namespaces_and_correlation():
    from feishu.events import EventPolicy, filter_event

    a = decide(payload()).envelope
    data = payload(message_id=None)
    data["header"]["event_id"] = "om_1"
    b = decide(data).envelope
    data = payload()
    data["header"]["app_id"] = "cli_other"
    c = filter_event(data, policy=EventPolicy(app_id="cli_other", bot_open_id="ou_bot")).envelope
    assert len({a.dedup_identity, b.dedup_identity, c.dedup_identity}) == 3
    assert len({a.request_id, b.request_id, c.request_id}) == 3
    data = payload()
    data["header"]["event_id"] = "ev_other"
    assert decide(data).envelope.request_id == a.request_id


@pytest.mark.parametrize(
    ("path", "value", "reason"),
    [
        ("schema", "1.0", "unsupported_schema"),
        ("header.event_type", "other", "unsupported_event"),
        ("header.app_id", "cli_other", "other_app"),
        ("event.sender.sender_type", "bot", "bot_sender"),
        ("event.sender.sender_type", "app", "unsupported_sender"),
        ("event.sender.sender_id.open_id", "ou_bot", "self_sender"),
        ("event.message.message_type", "image", "unsupported_message"),
        ("event.message.chat_type", "thread", "unsupported_chat"),
    ],
)
def test_ignored_messages_do_not_decode_bad_content(path, value, reason):
    data = payload(content="not JSON")
    set_path(data, path, value)
    result = decide(data)
    assert (result.status, result.reason, result.envelope) == ("ignored", reason, None)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("header", None),
        ("header.app_id", 12),
        ("event", []),
        ("event.sender", None),
        ("event.message", []),
        ("event.sender.sender_id", None),
        ("event.sender.sender_id.open_id", ""),
        ("event.sender.sender_type", None),
        ("event.message.message_type", None),
        ("event.message.chat_type", None),
        ("event.message.chat_id", ""),
        ("event.message.chat_id", "oc:bad"),
        ("event.message.message_id", 1),
        ("event.message.message_id", " om_1"),
        ("header.event_id", []),
        ("header.event_id", "a" * 257),
    ],
)
def test_malformed_fields_are_rejected_without_input(path, value):
    data = payload("SENSITIVE-TEXT")
    set_path(data, path, value)
    result = decide(data)
    assert result.status == "rejected" and result.envelope is None
    assert "SENSITIVE-TEXT" not in result.model_dump_json()


@pytest.mark.parametrize("data", [None, [], "raw", {}, {"schema": "2.0"}])
def test_malformed_root(data):
    assert decide(data).status == "rejected"


def test_no_ids_rejected():
    data = payload(message_id=" ")
    data["header"]["event_id"] = None
    assert decide(data).reason == "missing_identity"


@pytest.mark.parametrize(
    "content",
    [
        None,
        {},
        "{",
        "[]",
        "null",
        '"text"',
        '{"text":null}',
        '{"text":7}',
        "{}",
        '{"text":"safe","text":"bad"}',
        "[" * 1500 + "0" + "]" * 1500,
        '{"text":"\\ud800"}',
    ],
)
def test_invalid_content(content):
    result = decide(payload(content=content))
    assert (result.status, result.reason) == ("rejected", "invalid_content")


@pytest.mark.parametrize(
    ("text", "reason"), [("", "empty_text"), (" \n\t", "empty_text"), ("a" * 4001, "text_too_long")]
)
def test_text_limits(text, reason):
    assert decide(payload(text)).reason == reason


def test_text_and_content_size_boundaries():
    assert decide(payload("a" * 4000)).status == "accepted"
    content = json.dumps({"text": "ok"})
    assert decide(payload(content=content + " " * (32768 - len(content)))).status == "accepted"
    assert (
        decide(payload(content=content + " " * (32769 - len(content)))).reason
        == "content_too_large"
    )
    content = json.dumps({"text": "中", "unused": "中" * 11000}, ensure_ascii=False)
    assert decide(payload(content=content)).reason == "content_too_large"


def test_group_removes_only_complete_bot_tokens_and_keeps_other_text():
    data = payload(
        "@_user_1 问题 @_user_10 @_user_2\n@_user_1",
        chat_type="group",
        mentions=[mention(), mention("@_user_2", "ou_other")],
    )
    msg = decide(data).envelope
    assert msg.text == "问题 @_user_10 @_user_2"


@pytest.mark.parametrize("mentions", [None, [], [mention(open_id="ou_other")]])
def test_group_requires_actual_bot_mention(mentions):
    result = decide(payload("@_user_1 question", chat_type="group", mentions=mentions))
    assert (result.status, result.reason) == ("ignored", "not_addressed")


@pytest.mark.parametrize("text", ["question", "@_user_10 question", "@_user_1suffix question"])
def test_mention_metadata_alone_is_not_addressed(text):
    assert decide(payload(text, chat_type="group", mentions=[mention()])).reason == "not_addressed"


@pytest.mark.parametrize(
    "mentions",
    [
        {},
        [None],
        [{}],
        [mention(key="")],
        [mention(key="@_user_0")],
        [mention(open_id="")],
        [mention(), mention(open_id="ou_other")],
        [mention()] * 101,
    ],
)
def test_bad_group_mentions(mentions):
    assert (
        decide(payload("@_user_1 q", chat_type="group", mentions=mentions)).reason
        == "invalid_mentions"
    )


def test_mention_only_is_empty_and_p2p_does_not_parse_mentions():
    assert (
        decide(payload("@_user_1", chat_type="group", mentions=[mention()])).reason == "empty_text"
    )
    assert decide(payload(mentions="unused")).status == "accepted"
    assert (
        decide(payload("@_user_1 q", chat_type="group", mentions=[mention()] * 100)).status
        == "accepted"
    )


@pytest.mark.parametrize(
    "values",
    [
        {"app_id": "", "bot_open_id": "ou_bot"},
        {"app_id": "cli_test", "bot_open_id": None},
        {"app_id": "cli_test", "bot_open_id": "ou_bot", "extra": 1},
    ],
)
def test_invalid_policy(values):
    from feishu.events import EventPolicy

    with pytest.raises(ValidationError):
        EventPolicy(**values)


def test_dto_consistency_and_strictness():
    from feishu.events import EventDecision, MessageEnvelope

    valid = decide(payload()).envelope.model_dump()
    for override in (
        {"message_id": None, "event_id": None},
        {"text": " "},
        {"sender_type": "bot"},
        {"extra": "bad"},
        {"text": 123},
        {"request_id": UUID(int=1)},
        {"text": "\ud800"},
    ):
        with pytest.raises(ValidationError):
            MessageEnvelope.model_validate({**valid, **override})
    for fields in (
        {"status": "accepted", "reason": "eligible"},
        {"status": "ignored", "reason": "eligible"},
        {"status": "ignored", "reason": "bot_sender", "envelope": valid},
        {"status": "rejected", "reason": "bot_sender"},
    ):
        with pytest.raises(ValidationError):
            EventDecision(**fields)


@pytest.mark.parametrize(
    "path",
    [
        "schema",
        "header.event_type",
        "header.app_id",
        "event",
        "event.sender",
        "event.message",
        "event.sender.sender_id",
        "event.sender.sender_id.open_id",
        "event.sender.sender_type",
        "event.message.chat_id",
        "event.message.chat_type",
        "event.message.message_type",
        "event.message.content",
    ],
)
def test_required_fields_are_not_inferred(path):
    data = payload()
    parts = path.split(".")
    target = data
    for part in parts[:-1]:
        target = target[part]
    del target[parts[-1]]
    assert decide(data).status == "rejected"


def test_bot_without_user_identity_and_ignored_event_without_body():
    data = payload()
    data["event"]["sender"] = {"sender_type": "bot"}
    assert decide(data).reason == "bot_sender"
    data = {"schema": "2.0", "header": {"event_type": "other"}}
    assert decide(data).reason == "unsupported_event"
    data["header"] = {"event_type": "im.message.receive_v1", "app_id": "cli_other"}
    assert decide(data).reason == "other_app"


def test_raw_surrogate_is_controlled_and_identifier_boundary_is_preserved():
    assert decide(payload(content='{"text":"\ud800"}')).reason == "invalid_content"
    data = payload(message_id="m" * 256)
    assert decide(data).envelope.message_id == "m" * 256
    data["event"]["message"]["message_id"] = "m" * 257
    assert decide(data).status == "rejected"


def test_mutated_policy_and_envelope_are_revalidated():
    from feishu.events import EventPolicy, MessageEnvelope, filter_event

    policy = EventPolicy(app_id="cli_test", bot_open_id="ou_bot")
    policy.bot_open_id = ""
    with pytest.raises(ValidationError):
        filter_event(payload(), policy=policy)
    envelope = decide(payload()).envelope
    envelope.message_id = "different"
    with pytest.raises(ValidationError):
        MessageEnvelope.model_validate(envelope)
