from __future__ import annotations

from textwrap import dedent

from .models import ScoredReport


def build_plaintext_report(report: ScoredReport) -> str:
    signal_lines = []
    if report.signals:
        for signal in report.signals:
            sign = "+" if signal.score > 0 else ""
            signal_lines.append(
                f"- {signal.name}: {sign}{signal.score} ({signal.value}) | {signal.rationale}"
            )
    else:
        signal_lines.append("- No scored signals were available. Report should be treated as incomplete.")

    facts = "\n".join(f"- {fact}" for fact in report.key_facts) or "- No key facts available."
    notes = "\n".join(f"- {note}" for note in report.snapshot.manual_notes) or "- None."

    return dedent(
        f"""
        BTC Macro Daily Report | {report.snapshot.as_of}
        Regime: {report.regime}
        Total score: {report.total_score}
        Probability view: {report.probability_view}

        Key facts
        {facts}

        Signal breakdown
        {chr(10).join(signal_lines)}

        Manual notes
        {notes}
        """
    ).strip()


def build_slack_blocks(report: ScoredReport, body: str) -> list[dict]:
    signal_summary = "\n".join(
        f"* {signal.name}: {signal.score:+d} | {signal.value}" for signal in report.signals[:8]
    ) or "* No scored signals available"

    facts_summary = "\n".join(f"* {fact}" for fact in report.key_facts[:5]) or "* No key facts available"

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "BTC Macro Daily Report"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Date*\n{report.snapshot.as_of}"},
                {"type": "mrkdwn", "text": f"*Regime*\n{report.regime}"},
                {"type": "mrkdwn", "text": f"*Total Score*\n{report.total_score}"},
                {"type": "mrkdwn", "text": f"*Probability View*\n{report.probability_view}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Key Facts*\n{facts_summary}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Signal Breakdown*\n{signal_summary}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Narrative*\n```{body}```"},
        },
    ]
