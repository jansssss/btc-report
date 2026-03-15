from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Signal:
    name: str
    score: int
    status: str
    value: str
    rationale: str
    source: str


@dataclass(frozen=True)
class MarketSnapshot:
    as_of: str
    btc_price_usd: float | None
    btc_weekly_close_usd: float | None
    etf_net_flow_usd_millions: float | None
    oil_price_usd: float | None
    oil_5d_avg_usd: float | None
    oil_last_date: str | None
    us10y_yield_pct: float | None
    us10y_5d_change_bps: float | None
    us10y_last_date: str | None
    cpi_yoy_pct: float | None
    cpi_prev_yoy_pct: float | None
    cpi_last_date: str | None
    fear_greed_value: int | None
    fear_greed_label: str | None
    funding_rate_pct: float | None
    fed_hawkish: bool | None
    geopolitical_risk_up: bool | None
    manual_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScoredReport:
    total_score: int
    regime: str
    prob_150k: str
    risk_120k: str
    signals: list[Signal]
    snapshot: MarketSnapshot
    key_facts: list[str]

    def to_prompt_payload(self) -> dict[str, Any]:
        return {
            "date": self.snapshot.as_of,
            "total_score": self.total_score,
            "regime": self.regime,
            "prob_150k": self.prob_150k,
            "risk_120k": self.risk_120k,
            "signals": [
                {
                    "name": signal.name,
                    "score": signal.score,
                    "status": signal.status,
                    "value": signal.value,
                    "rationale": signal.rationale,
                }
                for signal in self.signals
            ],
            "key_facts": self.key_facts,
            "manual_notes": self.snapshot.manual_notes,
        }
