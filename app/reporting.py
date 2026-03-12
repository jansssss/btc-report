from __future__ import annotations

from textwrap import dedent

from .models import ScoredReport


_REGIME_EMOJI = {"강세 우위": "🟢", "중립": "🟡", "리스크 오프": "🔴"}
_PROB_EMOJI = {"상향": "📈", "보통": "➡️", "하향": "📉"}
_RISK_EMOJI = {"낮음": "🟢", "보통": "🟡", "높음": "🔴"}


def _score_bar(score: int) -> str:
    """Generate a colored emoji progress bar for the score (-6 to +6)."""
    MIN_S, MAX_S, RISK_T, BULL_T = -6, 6, -3, 3
    clamped = max(MIN_S, min(MAX_S, score))

    cells = []
    for s in range(MIN_S, MAX_S + 1):
        if s == clamped:
            cells.append("🔵")
        elif s < RISK_T:
            cells.append("🟥")
        elif s >= BULL_T:
            cells.append("🟩")
        else:
            cells.append("🟨")

    return "".join(cells) + "\n🔴 리스크오프(-3) │ 중립(0) │ 강세(+3) 🟢"


def build_plaintext_report(report: ScoredReport) -> str:
    signal_lines = "\n".join(
        f"{'▲' if s.score > 0 else '▼'} {s.name}: {s.score:+d}"
        for s in report.signals
    ) or "- 유효한 시그널 없음"

    facts = "\n".join(f"• {f}" for f in report.key_facts) or "• 데이터 없음"

    return dedent(
        f"""
        📊 BTC Macro Daily Report | {report.snapshot.as_of}

        총점: {report.total_score:+d}  |  판정: {report.regime}
        {_score_bar(report.total_score)}

        150k 조건부 확률: {report.prob_150k}
        120k 지연 리스크: {report.risk_120k}

        📌 핵심 수치
        {facts}

        ⚡ 핵심 기여 요인
        {signal_lines}
        """
    ).strip()


def build_slack_blocks(report: ScoredReport, interpretation: str) -> list[dict]:
    regime_emoji = _REGIME_EMOJI.get(report.regime, "⚪")
    prob_emoji = _PROB_EMOJI.get(report.prob_150k, "")
    risk_emoji = _RISK_EMOJI.get(report.risk_120k, "")

    score_str = f"{report.total_score:+d}"
    bar = _score_bar(report.total_score)

    signal_lines = "\n".join(
        f"{'🔺' if s.score > 0 else '🔻'} {s.name}: {s.score:+d}"
        for s in report.signals
    ) or "• 유효한 시그널 없음"

    facts_lines = "\n".join(f"• {f}" for f in report.key_facts) or "• 데이터 없음"

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📊 BTC Macro Daily Report"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{report.snapshot.as_of}*\n\n"
                    f"*총점:* {score_str}  |  *판정:* {regime_emoji} {report.regime}\n"
                    f"{bar}\n\n"
                    f"*150k 조건부 확률:* {prob_emoji} {report.prob_150k}　　"
                    f"*120k 지연 리스크:* {risk_emoji} {report.risk_120k}"
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"📌 *핵심 수치*\n{facts_lines}"},
                {"type": "mrkdwn", "text": f"⚡ *핵심 기여 요인*\n{signal_lines}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"💬 *해석*\n{interpretation}"},
        },
    ]
