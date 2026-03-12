from __future__ import annotations

from .http import post_json
from .models import ScoredReport


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def maybe_generate_summary(report: ScoredReport, *, api_key: str | None, model: str, enabled: bool) -> str | None:
    if not enabled or not api_key:
        return None

    instructions = (
        "You are writing a daily BTC macro Slack report. "
        "Do not change any scores or facts. "
        "Use only the provided JSON-equivalent facts. "
        "Keep the report under 120 words. "
        "Include: one-line summary, 2-3 driver sentences, one conditional probability sentence."
    )

    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": instructions}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": str(report.to_prompt_payload())}],
            },
        ],
    }
    response = post_json(
        OPENAI_RESPONSES_URL,
        payload=payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    return _extract_text(response)


def _extract_text(response: dict) -> str | None:
    for item in response.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if text:
                return text.strip()
    return None
