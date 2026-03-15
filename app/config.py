from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Settings:
    fred_api_key: str | None
    slack_bot_token: str | None
    slack_channel_id: str | None
    openai_api_key: str | None
    openai_model: str
    repo_root: Path
    manual_context_path: Path | None
    score_bull_threshold: int
    score_risk_threshold: int
    weekly_breakout_threshold: float
    oil_stable_threshold: float
    oil_risk_threshold: float
    etf_positive_threshold: float
    etf_negative_threshold: float
    ten_year_change_threshold_bps: float
    cpi_cooling_threshold: float
    fear_greed_extreme_greed_threshold: int
    fear_greed_extreme_fear_threshold: int
    funding_rate_overheating_pct: float
    use_llm: bool

    @classmethod
    def load(cls) -> "Settings":
        repo_root = Path(__file__).resolve().parent.parent
        _load_dotenv(repo_root / ".env")

        manual_context_env = os.getenv("MANUAL_CONTEXT_PATH")
        manual_context_path = (
            (repo_root / manual_context_env).resolve()
            if manual_context_env
            else repo_root / "data" / "manual_context.json"
        )

        return cls(
            fred_api_key=os.getenv("FRED_API_KEY"),
            slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
            slack_channel_id=os.getenv("SLACK_CHANNEL_ID"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            repo_root=repo_root,
            manual_context_path=manual_context_path,
            score_bull_threshold=int(os.getenv("SCORE_BULL_THRESHOLD", "3")),
            score_risk_threshold=int(os.getenv("SCORE_RISK_THRESHOLD", "-3")),
            weekly_breakout_threshold=float(os.getenv("WEEKLY_BREAKOUT_THRESHOLD", "126000")),
            oil_stable_threshold=float(os.getenv("OIL_STABLE_THRESHOLD", "90")),
            oil_risk_threshold=float(os.getenv("OIL_RISK_THRESHOLD", "100")),
            etf_positive_threshold=float(os.getenv("ETF_POSITIVE_THRESHOLD", "0")),
            etf_negative_threshold=float(os.getenv("ETF_NEGATIVE_THRESHOLD", "0")),
            ten_year_change_threshold_bps=float(os.getenv("TEN_YEAR_CHANGE_THRESHOLD_BPS", "-5")),
            cpi_cooling_threshold=float(os.getenv("CPI_COOLING_THRESHOLD", "0")),
            fear_greed_extreme_greed_threshold=int(os.getenv("FEAR_GREED_EXTREME_GREED_THRESHOLD", "80")),
            fear_greed_extreme_fear_threshold=int(os.getenv("FEAR_GREED_EXTREME_FEAR_THRESHOLD", "20")),
            funding_rate_overheating_pct=float(os.getenv("FUNDING_RATE_OVERHEATING_PCT", "0.05")),
            use_llm=os.getenv("USE_LLM_SUMMARY", "false").lower() == "true",
        )

    def load_manual_context(self) -> dict[str, Any]:
        return _read_json(self.manual_context_path)
