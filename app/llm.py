from __future__ import annotations

import json

from .http import post_json
from .models import LLMJudgment, ScoredReport


OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

_VALID_REGIME = {"강세 우위", "중립", "리스크 오프"}
_VALID_PROB = {"상향", "보통", "하향"}
_VALID_RISK = {"낮음", "보통", "높음"}

SYSTEM_PROMPT = """\
당신은 BTC 거시 환경 분석 전문가입니다.
제공된 원시 시장 데이터와 시그널을 종합적으로 판단하여 아래 JSON 형식으로만 응답하세요.

{
  "regime": "강세 우위" | "중립" | "리스크 오프",
  "prob_150k": "상향" | "보통" | "하향",
  "risk_120k": "낮음" | "보통" | "높음",
  "narrative": "4~5문장 한국어 해석"
}

판단 기준:
- regime: 매크로 시그널 전체를 종합하여 현재 시장 국면 판단
- prob_150k: BTC 현재 가격에서 $150,000까지의 거리를 반드시 고려할 것.
  예) BTC $67,380 → $150,000까지 +122% 필요 → 매크로가 아무리 좋아도 단기 "상향"은 과도함.
  BTC가 $100k 미만이면 "보통" 또는 "하향"이 원칙. $120k 이상일 때만 "상향" 적합.
- risk_120k: $120,000 지지 또는 조정 지연 가능성
- narrative: 수치를 직접 인용할 것. 현재 BTC 가격과 목표가($150k)의 괴리를 솔직히 언급.
  매크로 시그널과 실제 가격 사이의 간극을 전문가적 시각으로 설명. 기계적 판정 반복 금지.

JSON 외 다른 텍스트는 출력하지 마세요.\
"""


def maybe_generate_judgment(
    report: ScoredReport,
    *,
    api_key: str | None,
    model: str,
) -> LLMJudgment | None:
    if not api_key:
        return None

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(report.to_prompt_payload(), ensure_ascii=False)},
        ],
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
    }
    response = post_json(
        OPENAI_CHAT_URL,
        payload=payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    return _parse_judgment(response)


def _parse_judgment(response: dict) -> LLMJudgment | None:
    choices = response.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content", "").strip()
    if not content:
        return None

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None

    regime = data.get("regime", "")
    prob_150k = data.get("prob_150k", "")
    risk_120k = data.get("risk_120k", "")
    narrative = data.get("narrative", "").strip()

    if regime not in _VALID_REGIME or prob_150k not in _VALID_PROB or risk_120k not in _VALID_RISK or not narrative:
        return None

    return LLMJudgment(regime=regime, prob_150k=prob_150k, risk_120k=risk_120k, narrative=narrative)
