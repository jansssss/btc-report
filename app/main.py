from __future__ import annotations

import argparse
import json

from .config import Settings
from .data_sources import DataCollector
from .llm import maybe_generate_summary
from .reporting import build_plaintext_report, build_slack_blocks
from .scoring import score_snapshot
from .slack import send_message


def run(*, dry_run: bool) -> int:
    settings = Settings.load()
    collector = DataCollector(settings)
    snapshot = collector.build_snapshot()
    report = score_snapshot(snapshot, settings)

    narrative = maybe_generate_summary(
        report,
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        enabled=settings.use_llm,
    ) or build_plaintext_report(report)

    output = {
        "report": report.to_prompt_payload(),
        "narrative": narrative,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if dry_run:
        return 0

    if not settings.slack_bot_token or not settings.slack_channel_id:
        raise RuntimeError("SLACK_BOT_TOKEN and SLACK_CHANNEL_ID are required when dry-run is false.")

    send_message(
        token=settings.slack_bot_token,
        channel_id=settings.slack_channel_id,
        text=narrative,
        blocks=build_slack_blocks(report, narrative),
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and send the daily BTC macro report.")
    parser.add_argument("--dry-run", action="store_true", help="Print the report but do not send Slack message.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(dry_run=parse_args().dry_run))
