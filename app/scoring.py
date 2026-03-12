from __future__ import annotations

from .config import Settings
from .models import MarketSnapshot, ScoredReport, Signal


def score_snapshot(snapshot: MarketSnapshot, settings: Settings) -> ScoredReport:
    signals: list[Signal] = []

    if snapshot.oil_5d_avg_usd is not None and snapshot.oil_5d_avg_usd <= settings.oil_stable_threshold:
        signals.append(
            Signal(
                name="유가 안정",
                score=1,
                status="positive",
                value=f"5일 평균 ${snapshot.oil_5d_avg_usd:.2f}",
                rationale=f"WTI 5일 평균이 ${settings.oil_stable_threshold:.0f} 이하 유지.",
                source="FRED DCOILWTICO",
            )
        )
    elif snapshot.oil_price_usd is not None and snapshot.oil_price_usd >= settings.oil_risk_threshold:
        signals.append(
            Signal(
                name="유가 급등",
                score=-2,
                status="negative",
                value=f"현물 ${snapshot.oil_price_usd:.2f}",
                rationale=f"WTI가 ${settings.oil_risk_threshold:.0f} 돌파.",
                source="FRED DCOILWTICO",
            )
        )

    if snapshot.etf_net_flow_usd_millions is not None and snapshot.etf_net_flow_usd_millions > settings.etf_positive_threshold:
        signals.append(
            Signal(
                name="ETF 순유입",
                score=2,
                status="positive",
                value=f"${snapshot.etf_net_flow_usd_millions:.1f}M",
                rationale="현물 ETF 자금 순유입 전환.",
                source="Farside BTC ETF flows",
            )
        )
    elif snapshot.etf_net_flow_usd_millions is not None and snapshot.etf_net_flow_usd_millions < settings.etf_negative_threshold:
        signals.append(
            Signal(
                name="ETF 순유출",
                score=-2,
                status="negative",
                value=f"${snapshot.etf_net_flow_usd_millions:.1f}M",
                rationale="현물 ETF 자금 순유출 지속.",
                source="Farside BTC ETF flows",
            )
        )

    if snapshot.us10y_5d_change_bps is not None and snapshot.us10y_5d_change_bps <= settings.ten_year_change_threshold_bps:
        signals.append(
            Signal(
                name="미 10년물 하락",
                score=1,
                status="positive",
                value=f"{snapshot.us10y_5d_change_bps:.1f} bps / 5일",
                rationale="5거래일 기준 장기금리 완화.",
                source="FRED DGS10",
            )
        )

    if snapshot.fed_hawkish is True:
        signals.append(
            Signal(
                name="연준 매파",
                score=-2,
                status="negative",
                value="매파적",
                rationale="최근 연준 발언이 매파적으로 분류됨.",
                source="manual_context.json",
            )
        )

    if snapshot.cpi_yoy_pct is not None and snapshot.cpi_prev_yoy_pct is not None:
        if snapshot.cpi_yoy_pct <= snapshot.cpi_prev_yoy_pct + settings.cpi_cooling_threshold:
            signals.append(
                Signal(
                    name="CPI 둔화",
                    score=2,
                    status="positive",
                    value=f"{snapshot.cpi_prev_yoy_pct:.2f}% → {snapshot.cpi_yoy_pct:.2f}%",
                    rationale="직전 월 대비 물가 상승세 둔화.",
                    source="FRED CPIAUCSL",
                )
            )

    if snapshot.geopolitical_risk_up is True:
        signals.append(
            Signal(
                name="지정학 리스크",
                score=-2,
                status="negative",
                value="상승",
                rationale="지정학 리스크 확대 수동 플래그 설정.",
                source="manual_context.json",
            )
        )

    if snapshot.btc_weekly_close_usd is not None and snapshot.btc_weekly_close_usd > settings.weekly_breakout_threshold:
        signals.append(
            Signal(
                name="주봉 돌파",
                score=2,
                status="positive",
                value=f"${snapshot.btc_weekly_close_usd:,.0f}",
                rationale=f"BTC 주봉 종가 ${settings.weekly_breakout_threshold:,.0f} 상회.",
                source="CoinGecko market chart",
            )
        )

    total_score = sum(signal.score for signal in signals)
    if total_score >= settings.score_bull_threshold:
        regime = "강세 우위"
        prob_150k = "상향"
        risk_120k = "낮음"
    elif total_score <= settings.score_risk_threshold:
        regime = "리스크 오프"
        prob_150k = "하향"
        risk_120k = "높음"
    else:
        regime = "중립"
        prob_150k = "보통"
        risk_120k = "보통"

    key_facts = _build_key_facts(snapshot)
    return ScoredReport(
        total_score=total_score,
        regime=regime,
        prob_150k=prob_150k,
        risk_120k=risk_120k,
        signals=signals,
        snapshot=snapshot,
        key_facts=key_facts,
    )


def _build_key_facts(snapshot: MarketSnapshot) -> list[str]:
    facts: list[str] = []
    if snapshot.btc_price_usd is not None:
        facts.append(f"BTC 현물: ${snapshot.btc_price_usd:,.0f}")
    if snapshot.etf_net_flow_usd_millions is not None:
        facts.append(f"현물 ETF 순자금: ${snapshot.etf_net_flow_usd_millions:.1f}M")
    if snapshot.oil_5d_avg_usd is not None:
        facts.append(f"WTI 5일 평균: ${snapshot.oil_5d_avg_usd:.2f}")
    if snapshot.us10y_yield_pct is not None:
        facts.append(f"미 10년물: {snapshot.us10y_yield_pct:.2f}%")
    if snapshot.cpi_yoy_pct is not None:
        facts.append(f"CPI YoY: {snapshot.cpi_yoy_pct:.2f}%")
    return facts
