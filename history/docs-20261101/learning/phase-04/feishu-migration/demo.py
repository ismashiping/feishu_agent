"""Offline demo of the real Feishu event boundary."""

from __future__ import annotations

import json

from clinical_agent.channels.feishu.events import EventPolicy, filter_event


def payload() -> dict[str, object]:
    return {
        "schema": "2.0",
        "header": {
            "event_type": "im.message.receive_v1",
            "app_id": "app_demo",
            "event_id": "event_demo",
        },
        "event": {
            "sender": {
                "sender_type": "user",
                "sender_id": {"open_id": "user_demo"},
            },
            "message": {
                "message_id": "message_demo",
                "chat_id": "chat_demo",
                "chat_type": "p2p",
                "message_type": "text",
                "content": json.dumps({"text": "  比较两种研究方法  "}, ensure_ascii=False),
                "mentions": None,
            },
        },
    }


def main() -> None:
    policy = EventPolicy(app_id="app_demo", bot_open_id="bot_demo")
    first = filter_event(payload(), policy=policy)
    second = filter_event(payload(), policy=policy)
    assert first.envelope is not None and second.envelope is not None
    assert first.envelope.request_id == second.envelope.request_id

    print(f"decision={first.status}:{first.reason}")
    print(f"text={first.envelope.text}")
    print(f"stable_request_id={first.envelope.request_id}")


if __name__ == "__main__":
    main()
