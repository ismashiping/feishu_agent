"""Pure filtering of decoded receive-message events before admission and deduplication."""

import json
import re
from typing import Annotated, Literal, Self, get_args
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import StringConstraints, ValidationError, field_validator, model_validator

from clinical_agent.domain.models import DTO

Identifier = Annotated[
    str, StringConstraints(strict=True, min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")
]
MessageText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)
]
IgnoredReason = Literal[
    "unsupported_event",
    "unsupported_schema",
    "other_app",
    "self_sender",
    "bot_sender",
    "unsupported_sender",
    "unsupported_message",
    "unsupported_chat",
    "not_addressed",
]
RejectedReason = Literal[
    "invalid_event",
    "invalid_content",
    "content_too_large",
    "invalid_mentions",
    "empty_text",
    "text_too_long",
    "missing_identity",
]
Reason = Literal["eligible"] | IgnoredReason | RejectedReason
IGNORED = frozenset(get_args(IgnoredReason))
REJECTED = frozenset(get_args(RejectedReason))


class EventPolicy(DTO):
    app_id: Identifier
    bot_open_id: Identifier


def _request_id(identity: tuple[str, str, str]) -> UUID:
    return uuid5(NAMESPACE_URL, json.dumps(identity, ensure_ascii=True, separators=(",", ":")))


class MessageEnvelope(DTO):
    app_id: Identifier
    message_id: Identifier | None = None
    event_id: Identifier | None = None
    sender_id: Identifier
    sender_type: Literal["user"] = "user"
    chat_id: Identifier
    chat_type: Literal["p2p", "group"]
    message_type: Literal["text"] = "text"
    text: MessageText
    request_id: UUID

    @field_validator("message_id", "event_id", mode="before")
    @classmethod
    def empty_id(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("text")
    @classmethod
    def unicode_text(cls, value: str) -> str:
        value.encode("utf-8")
        return value

    @property
    def dedup_identity(self) -> tuple[str, str, str]:
        if self.message_id is not None:
            return self.app_id, "message", self.message_id
        if self.event_id is not None:
            return self.app_id, "event", self.event_id
        raise ValueError("missing_identity")

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if self.request_id != _request_id(self.dedup_identity):
            raise ValueError("invalid_request_id")
        return self


class EventDecision(DTO):
    status: Literal["accepted", "ignored", "rejected"]
    reason: Reason
    envelope: MessageEnvelope | None = None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.status == "accepted":
            valid = self.reason == "eligible" and self.envelope is not None
        else:
            reasons = IGNORED if self.status == "ignored" else REJECTED
            valid = self.reason in reasons and self.envelope is None
        if not valid:
            raise ValueError("inconsistent_decision")
        return self


class _Invalid(ValueError):
    def __init__(self, reason: RejectedReason = "invalid_event") -> None:
        self.reason = reason
        super().__init__(reason)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _Invalid()
    return value


def _string(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise _Invalid()
    return value


def _identifier(value: object, *, optional: bool = False) -> str | None:
    if optional and (value is None or isinstance(value, str) and not value.strip()):
        return None
    text = _string(value)
    if len(text) > 256 or re.fullmatch(r"[A-Za-z0-9_-]+", text) is None:
        raise _Invalid()
    return text


def _stop(reason: IgnoredReason) -> EventDecision:
    return EventDecision(status="ignored", reason=reason)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _text(content: object) -> str:
    if not isinstance(content, str):
        raise _Invalid("invalid_content")
    try:
        size = len(content.encode("utf-8"))
    except UnicodeError:
        raise _Invalid("invalid_content") from None
    if size > 32768:
        raise _Invalid("content_too_large")
    try:
        value = json.loads(content, object_pairs_hook=_unique_object)
        if not isinstance(value, dict) or not isinstance(value.get("text"), str):
            raise ValueError("invalid_text")
        text: str = value["text"]
        text.encode("utf-8")
        return text
    except (ValueError, RecursionError, UnicodeError):
        raise _Invalid("invalid_content") from None


def _addressed_text(text: str, mentions: object, bot_open_id: str) -> str | None:
    if mentions is None:
        mentions = []
    if not isinstance(mentions, list) or len(mentions) > 100:
        raise _Invalid("invalid_mentions")
    identities: dict[str, str] = {}
    try:
        for item in mentions:
            entry = _object(item)
            key = _string(entry.get("key"))
            if len(key) > 256 or re.fullmatch(r"@_user_[1-9][0-9]*", key) is None:
                raise _Invalid()
            open_id = _identifier(_object(entry.get("id")).get("open_id"))
            assert open_id is not None
            if key in identities and identities[key] != open_id:
                raise _Invalid()
            identities[key] = open_id
    except _Invalid:
        raise _Invalid("invalid_mentions") from None
    keys = [re.escape(key) for key, identity in identities.items() if identity == bot_open_id]
    if not keys:
        return None
    pattern = r"(?<!\w)(?:" + "|".join(keys) + r")(?!\w)"
    if re.search(pattern, text) is None:
        return None
    return re.sub(pattern, "", text)


def filter_event(payload: object, *, policy: EventPolicy) -> EventDecision:
    """Return eligibility only; callers must still admit and atomically deduplicate."""
    policy = EventPolicy.model_validate(policy)
    try:
        data = _object(payload)
        header = _object(data.get("header"))
        if _string(header.get("event_type")) != "im.message.receive_v1":
            return _stop("unsupported_event")
        if _string(data.get("schema")) != "2.0":
            return _stop("unsupported_schema")
        app_id = _identifier(header.get("app_id"))
        if app_id != policy.app_id:
            return _stop("other_app")
        event = _object(data.get("event"))
        sender = _object(event.get("sender"))
        message = _object(event.get("message"))
        sender_type = _string(sender.get("sender_type"))
        # Bot events may lack a human open_id; never require it to ignore a bot.
        if sender_type == "bot":
            return _stop("bot_sender")
        if sender_type != "user":
            return _stop("unsupported_sender")
        sender_id = _identifier(_object(sender.get("sender_id")).get("open_id"))
        if sender_id == policy.bot_open_id:
            return _stop("self_sender")
        if _string(message.get("message_type")) != "text":
            return _stop("unsupported_message")
        chat_type = _string(message.get("chat_type"))
        if chat_type not in ("p2p", "group"):
            return _stop("unsupported_chat")
        chat_id = _identifier(message.get("chat_id"))
        text = _text(message.get("content"))
        if chat_type == "group":
            addressed = _addressed_text(text, message.get("mentions"), policy.bot_open_id)
            if addressed is None:
                return _stop("not_addressed")
            text = addressed
        text = text.strip()
        if not text:
            raise _Invalid("empty_text")
        if len(text) > 4000:
            raise _Invalid("text_too_long")
        message_id = _identifier(message.get("message_id"), optional=True)
        event_id = _identifier(header.get("event_id"), optional=True)
        if message_id is None and event_id is None:
            raise _Invalid("missing_identity")
        identity = (
            (policy.app_id, "message", message_id)
            if message_id
            else (policy.app_id, "event", str(event_id))
        )
        envelope = MessageEnvelope.model_validate(
            {
                "app_id": app_id,
                "message_id": message_id,
                "event_id": event_id,
                "sender_id": sender_id,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "text": text,
                "request_id": _request_id(identity),
            }
        )
        return EventDecision(status="accepted", reason="eligible", envelope=envelope)
    except _Invalid as exc:
        return EventDecision(status="rejected", reason=exc.reason)
    except ValidationError:
        return EventDecision(status="rejected", reason="invalid_event")
