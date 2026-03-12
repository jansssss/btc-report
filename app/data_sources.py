from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from .config import Settings
from .http import get_json
from .models import MarketSnapshot


COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_MARKET_CHART_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series/observations"
FARSIDE_BTC_URL = "https://farside.co.uk/btc/wp-json/farside/v1/flows"


@dataclass(frozen=True)
class FredObservation:
    date: str
    value: float


class DataCollector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.manual_context = settings.load_manual_context()

    def build_snapshot(self) -> MarketSnapshot:
        notes = [str(item) for item in self.manual_context.get("notes", [])]
        if not self.settings.fred_api_key:
            notes.append("FRED_API_KEY is not configured, so oil, rates, and CPI signals are skipped.")

        btc_price = self._safe(self._get_btc_spot_price, notes, "BTC spot")
        btc_weekly_close = self._safe(self._get_btc_last_weekly_close, notes, "BTC weekly close proxy")
        etf_flow = self._safe(self._get_etf_net_flow, notes, "ETF flow")
        oil_series = self._safe(lambda: self._get_fred_series("DCOILWTICO", limit=10), notes, "WTI series") or []
        us10y_series = self._safe(lambda: self._get_fred_series("DGS10", limit=10), notes, "US 10Y series") or []
        cpi_series = self._safe(lambda: self._get_fred_series("CPIAUCSL", limit=15), notes, "CPI series") or []

        oil_latest = oil_series[-1].value if oil_series else None
        oil_5d_avg = mean(point.value for point in oil_series[-5:]) if len(oil_series) >= 5 else oil_latest
        us10y_latest = us10y_series[-1].value if us10y_series else None
        us10y_5d_change_bps = None
        if len(us10y_series) >= 5:
            us10y_5d_change_bps = round((us10y_series[-1].value - us10y_series[-5].value) * 100, 1)

        cpi_latest = cpi_series[-1].value if cpi_series else None
        cpi_prev = cpi_series[-2].value if len(cpi_series) >= 2 else None

        return MarketSnapshot(
            as_of=datetime.now(timezone.utc).date().isoformat(),
            btc_price_usd=btc_price,
            btc_weekly_close_usd=btc_weekly_close,
            etf_net_flow_usd_millions=etf_flow,
            oil_price_usd=oil_latest,
            oil_5d_avg_usd=oil_5d_avg,
            us10y_yield_pct=us10y_latest,
            us10y_5d_change_bps=us10y_5d_change_bps,
            cpi_yoy_pct=self._cpi_yoy(cpi_series),
            cpi_prev_yoy_pct=self._cpi_prev_yoy(cpi_series),
            fed_hawkish=self._manual_bool("fed_hawkish"),
            geopolitical_risk_up=self._manual_bool("geopolitical_risk_up"),
            manual_notes=notes,
        )

    def _safe(self, func, notes: list[str], label: str):
        try:
            return func()
        except Exception as exc:
            notes.append(f"{label} unavailable: {exc}")
            return None

    def _manual_bool(self, key: str) -> bool | None:
        value = self.manual_context.get(key)
        if value is None:
            return None
        return bool(value)

    def _get_btc_spot_price(self) -> float | None:
        data = get_json(COINGECKO_PRICE_URL, params={"ids": "bitcoin", "vs_currencies": "usd"})
        return data.get("bitcoin", {}).get("usd")

    def _get_btc_last_weekly_close(self) -> float | None:
        data = get_json(
            COINGECKO_MARKET_CHART_URL,
            params={"vs_currency": "usd", "days": "14", "interval": "daily"},
        )
        prices = data.get("prices", [])
        if len(prices) < 8:
            return None
        # Approximation: use the prior 7th daily close as last completed weekly close proxy.
        return round(float(prices[-8][1]), 2)

    def _get_etf_net_flow(self) -> float | None:
        try:
            data = get_json(FARSIDE_BTC_URL)
        except Exception:
            return self._manual_float("etf_net_flow_usd_millions")

        if not isinstance(data, list) or not data:
            return self._manual_float("etf_net_flow_usd_millions")

        latest = data[-1]
        total = latest.get("total")
        if total is None:
            return self._manual_float("etf_net_flow_usd_millions")
        return float(total)

    def _manual_float(self, key: str) -> float | None:
        value = self.manual_context.get(key)
        return float(value) if value is not None else None

    def _get_fred_series(self, series_id: str, *, limit: int) -> list[FredObservation]:
        if not self.settings.fred_api_key:
            return []

        payload = get_json(
            FRED_SERIES_URL,
            params={
                "series_id": series_id,
                "api_key": self.settings.fred_api_key,
                "file_type": "json",
                "sort_order": "asc",
                "limit": limit * 3,
            },
        )
        rows = payload.get("observations", [])
        points: list[FredObservation] = []
        for row in rows:
            raw_value = row.get("value")
            if raw_value in (None, ".", ""):
                continue
            points.append(FredObservation(date=row["date"], value=float(raw_value)))
        return points[-limit:]

    def _cpi_yoy(self, series: list[FredObservation]) -> float | None:
        if len(series) < 13:
            return None
        latest = series[-1].value
        previous_year = series[-13].value
        return round(((latest / previous_year) - 1) * 100, 2)

    def _cpi_prev_yoy(self, series: list[FredObservation]) -> float | None:
        if len(series) < 14:
            return None
        previous = series[-2].value
        previous_year = series[-14].value
        return round(((previous / previous_year) - 1) * 100, 2)
