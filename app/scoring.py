from __future__ import annotations

from .config import Settings
from .models import MarketSnapshot, ScoredReport, Signal


def score_snapshot(snapshot: MarketSnapshot, settings: Settings) -> ScoredReport:
    signals: list[Signal] = []

    if snapshot.oil_5d_avg_usd is not None and snapshot.oil_5d_avg_usd <= settings.oil_stable_threshold:
        signals.append(
            Signal(
                name="Oil stability",
                score=1,
                status="positive",
                value=f"5d avg ${snapshot.oil_5d_avg_usd:.2f}",
                rationale=f"WTI stayed at or below ${settings.oil_stable_threshold:.0f}.",
                source="FRED DCOILWTICO",
            )
        )
    elif snapshot.oil_price_usd is not None and snapshot.oil_price_usd >= settings.oil_risk_threshold:
        signals.append(
            Signal(
                name="Oil spike",
                score=-2,
                status="negative",
                value=f"spot ${snapshot.oil_price_usd:.2f}",
                rationale=f"WTI moved above ${settings.oil_risk_threshold:.0f}.",
                source="FRED DCOILWTICO",
            )
        )

    if snapshot.etf_net_flow_usd_millions is not None and snapshot.etf_net_flow_usd_millions > settings.etf_positive_threshold:
        signals.append(
            Signal(
                name="ETF net inflow",
                score=2,
                status="positive",
                value=f"${snapshot.etf_net_flow_usd_millions:.1f}M",
                rationale="Spot ETF flows turned positive.",
                source="Farside BTC ETF flows",
            )
        )
    elif snapshot.etf_net_flow_usd_millions is not None and snapshot.etf_net_flow_usd_millions < settings.etf_negative_threshold:
        signals.append(
            Signal(
                name="ETF net outflow",
                score=-2,
                status="negative",
                value=f"${snapshot.etf_net_flow_usd_millions:.1f}M",
                rationale="Spot ETF flows stayed negative.",
                source="Farside BTC ETF flows",
            )
        )

    if snapshot.us10y_5d_change_bps is not None and snapshot.us10y_5d_change_bps <= settings.ten_year_change_threshold_bps:
        signals.append(
            Signal(
                name="US 10Y yield",
                score=1,
                status="positive",
                value=f"{snapshot.us10y_5d_change_bps:.1f} bps / 5d",
                rationale="Long-end yields eased over the last 5 trading days.",
                source="FRED DGS10",
            )
        )

    if snapshot.fed_hawkish is True:
        signals.append(
            Signal(
                name="Fed tone",
                score=-2,
                status="negative",
                value="hawkish",
                rationale="Manual context marked the latest Fed communication as hawkish.",
                source="manual_context.json",
            )
        )

    if snapshot.cpi_yoy_pct is not None and snapshot.cpi_prev_yoy_pct is not None:
        if snapshot.cpi_yoy_pct <= snapshot.cpi_prev_yoy_pct + settings.cpi_cooling_threshold:
            signals.append(
                Signal(
                    name="CPI trend",
                    score=2,
                    status="positive",
                    value=f"{snapshot.cpi_prev_yoy_pct:.2f}% -> {snapshot.cpi_yoy_pct:.2f}%",
                    rationale="Inflation momentum cooled versus the previous monthly print.",
                    source="FRED CPIAUCSL",
                )
            )

    if snapshot.geopolitical_risk_up is True:
        signals.append(
            Signal(
                name="Geopolitical risk",
                score=-2,
                status="negative",
                value="elevated",
                rationale="Manual context marked geopolitical risk as rising.",
                source="manual_context.json",
            )
        )

    if snapshot.btc_weekly_close_usd is not None and snapshot.btc_weekly_close_usd > settings.weekly_breakout_threshold:
        signals.append(
            Signal(
                name="Weekly breakout",
                score=2,
                status="positive",
                value=f"${snapshot.btc_weekly_close_usd:,.0f}",
                rationale=f"BTC weekly close proxy cleared ${settings.weekly_breakout_threshold:,.0f}.",
                source="CoinGecko market chart",
            )
        )

    total_score = sum(signal.score for signal in signals)
    if total_score >= settings.score_bull_threshold:
        regime = "bullish"
        probability_view = "150k conditional probability is rising toward the upper band."
    elif total_score <= settings.score_risk_threshold:
        regime = "risk-off"
        probability_view = "120k timing risk is increasing and 150k odds are being pushed back."
    else:
        regime = "neutral"
        probability_view = "Conditions are mixed, so the base-case probability range stays conservative."

    key_facts = _build_key_facts(snapshot)
    return ScoredReport(
        total_score=total_score,
        regime=regime,
        probability_view=probability_view,
        signals=signals,
        snapshot=snapshot,
        key_facts=key_facts,
    )


def _build_key_facts(snapshot: MarketSnapshot) -> list[str]:
    facts: list[str] = []
    if snapshot.btc_price_usd is not None:
        facts.append(f"BTC spot: ${snapshot.btc_price_usd:,.0f}")
    if snapshot.etf_net_flow_usd_millions is not None:
        facts.append(f"Spot BTC ETF net flow: ${snapshot.etf_net_flow_usd_millions:.1f}M")
    if snapshot.oil_5d_avg_usd is not None:
        facts.append(f"WTI 5d average: ${snapshot.oil_5d_avg_usd:.2f}")
    if snapshot.us10y_yield_pct is not None:
        facts.append(f"US 10Y yield: {snapshot.us10y_yield_pct:.2f}%")
    if snapshot.cpi_yoy_pct is not None:
        facts.append(f"CPI YoY proxy: {snapshot.cpi_yoy_pct:.2f}%")
    return facts
