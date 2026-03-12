from __future__ import annotations

from .http import post_json
from .models import ScoredReport


OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def maybe_generate_summary(report: ScoredReport, *, api_key: str | None, model: str, enabled: bool) -> str | None:
    if not enabled or not api_key:
        return None

    system_prompt = (
        "당신은 BTC 거시 환경을 분석하는 트레이딩 어시스턴트입니다. "
        "제공된 데이터만을 근거로 3~4문장의 한국어 해석을 작성하세요. "
        "점수나 수치를 임의로 변경하지 마세요. "
        "150k 도달 가능성과 120k 지연 리스크를 반드시 언급하세요. "
        "간결하고 전문적인 톤을 유지하세요."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": str(report.to_prompt_payload())},
        ],
        "max_tokens": 300,
    }
    response = post_json(
        OPENAI_CHAT_URL,
        payload=payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    return _extract_text(response)


def _extract_text(response: dict) -> str | None:
    choices = response.get("choices", [])
    if not choices:
        return None
    return choices[0].get("message", {}).get("content", "").strip() or None
