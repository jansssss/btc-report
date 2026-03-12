from __future__ import annotations

from textwrap import dedent

from .models import ScoredReport


def build_plaintext_report(report: ScoredReport) -> str:
    signal_lines = []
    if report.signals:
        for signal in report.signals:
            sign = "+" if signal.score > 0 else ""
            signal_lines.append(f"- {signal.name}: {sign}{signal.score}")
    else:
        signal_lines.append("- 유효한 시그널 없음. 리포트를 불완전 상태로 처리하세요.")

    facts = "\n".join(f"- {fact}" for fact in report.key_facts) or "- 데이터 없음."

    return dedent(
        f"""
        BTC Macro Daily Report | {report.snapshot.as_of}

        총점: {report.total_score:+d}
        판정: {report.regime}
        150k 조건부 확률: {report.prob_150k}
        120k 지연 리스크: {report.risk_120k}

        핵심 수치
        {facts}

        핵심 기여 요인
        {chr(10).join(signal_lines)}
        """
    ).strip()


def build_slack_blocks(report: ScoredReport, interpretation: str) -> list[dict]:
    signal_lines = "\n".join(
        f"- {s.name}: {s.score:+d}"
        for s in report.signals
    ) or "- 유효한 시그널 없음"

    facts_lines = "\n".join(f"- {f}" for f in report.key_facts) or "- 데이터 없음"

    score_str = f"{report.total_score:+d}" if report.total_score != 0 else "0"

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"BTC Macro Daily Report | {report.snapshot.as_of}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*총점*\n{score_str}"},
                {"type": "mrkdwn", "text": f"*판정*\n{report.regime}"},
                {"type": "mrkdwn", "text": f"*150k 조건부 확률*\n{report.prob_150k}"},
                {"type": "mrkdwn", "text": f"*120k 지연 리스크*\n{report.risk_120k}"},
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*핵심 수치*\n{facts_lines}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*핵심 기여 요인*\n{signal_lines}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*해석*\n{interpretation}"},
        },
    ]
