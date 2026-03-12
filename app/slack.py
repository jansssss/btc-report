from __future__ import annotations

from .http import post_json


SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


def send_message(*, token: str, channel_id: str, text: str, blocks: list[dict]) -> dict:
    response = post_json(
        SLACK_POST_MESSAGE_URL,
        payload={
            "channel": channel_id,
            "text": text,
            "blocks": blocks,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    if not response.get("ok"):
        raise RuntimeError(f"Slack API error: {response}")
    return response
