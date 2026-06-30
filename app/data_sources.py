from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from statistics import mean
from typing import Any

from .config import Settings
from .http import get_json, get_text
from .models import MarketSnapshot


COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"
COINGECKO_MARKET_CHART_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
FRED_SERIES_URL = "https://api.stlouisfed.org/fred/series/observations"
FARSIDE_BTC_URL = "https://farside.co.uk/btc/wp-json/farside/v1/flows"
ALTERNATIVE_ME_FNG_URL = "https://api.alternative.me/fng/"
BINANCE_PREMIUM_INDEX_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
NAVER_WORLD_DAILY_URL = "https://finance.naver.com/marketindex/worldDailyQuote.naver"
TREASURY_YIELD_CURVE_BASE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all"
KICS_TRADE_STATS_URL = "https://apis.data.go.kr/1220000/tradeStats/getTradeStatsList"
_SEMICON_HS4 = "8542"  # 집적회로 (반도체)

_NAVER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.naver.com/",
}
_ROW_RE = re.compile(r'<tr class="(?:up|down|same2)">(.*?)</tr>', re.DOTALL)
_DATE_RE = re.compile(r'(\d{4})\.(\d{2})\.(\d{2})')
_TD_NUM_RE = re.compile(r'<td class="num">(.*?)</td>', re.DOTALL)
_NUM_RE = re.compile(r'([\d,]+\.\d+)')


@dataclass(frozen=True)
class FredObservation:
    date: str
    value: float


def _parse_naver_price_table(html: str) -> list[FredObservation]:
    """Parse Naver Finance worldDailyQuote HTML table. Returns rows newest-first."""
    results = []
    for row_m in _ROW_RE.finditer(html):
        row_html = row_m.group(1)
        date_m = _DATE_RE.search(row_html)
        if not date_m:
            continue
        date_str = f"{date_m.group(1)}-{date_m.group(2)}-{date_m.group(3)}"
        price = None
        for cell in _TD_NUM_RE.findall(row_html):
            if "<img" not in cell:
                num_m = _NUM_RE.search(cell)
                if num_m:
                    price = float(num_m.group(1).replace(",", ""))
                    break
        if price and price > 0:
            results.append(FredObservation(date=date_str, value=price))
    return results


class DataCollector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.manual_context = settings.load_manual_context()

    def build_snapshot(self) -> MarketSnapshot:
        notes = [str(item) for item in self.manual_context.get("notes", [])]
        if not self.settings.fred_api_key:
            notes.append("FRED_API_KEY is not configured, so CPI signal is skipped.")

        btc_price = self._safe(self._get_btc_spot_price, notes, "BTC spot")
        btc_weekly_close = self._safe(self._get_btc_last_weekly_close, notes, "BTC weekly close proxy")
        etf_flow = self._safe(self._get_etf_net_flow, notes, "ETF flow")
        oil_series = self._safe(lambda: self._get_naver_series("OIL_CL", 2, limit=10), notes, "WTI series") or []
        us10y_series = self._safe(lambda: self._get_us10y_series_treasury(limit=10), notes, "US 10Y series") or []
        cpi_series = self._safe(lambda: self._get_fred_series("CPIAUCSL", limit=15), notes, "CPI series") or []
        fear_greed_result = self._safe(self._get_fear_greed, notes, "Fear & Greed")
        funding_rate = self._safe(self._get_funding_rate, notes, "Funding rate")
        semicon_result = self._safe(self._get_semiconductor_exports, notes, "반도체 수출")

        oil_latest = oil_series[-1].value if oil_series else None
        oil_last_date = oil_series[-1].date if oil_series else None
        oil_5d_avg = mean(point.value for point in oil_series[-5:]) if len(oil_series) >= 5 else oil_latest
        us10y_latest = us10y_series[-1].value if us10y_series else None
        us10y_last_date = us10y_series[-1].date if us10y_series else None
        us10y_5d_change_bps = None
        if len(us10y_series) >= 5:
            us10y_5d_change_bps = round((us10y_series[-1].value - us10y_series[-5].value) * 100, 1)

        cpi_latest = cpi_series[-1].value if cpi_series else None
        cpi_last_date = cpi_series[-1].date if cpi_series else None
        cpi_prev = cpi_series[-2].value if len(cpi_series) >= 2 else None

        return MarketSnapshot(
            as_of=datetime.now(timezone.utc).date().isoformat(),
            btc_price_usd=btc_price,
            btc_weekly_close_usd=btc_weekly_close,
            etf_net_flow_usd_millions=etf_flow,
            oil_price_usd=oil_latest,
            oil_5d_avg_usd=oil_5d_avg,
            oil_last_date=oil_last_date,
            us10y_yield_pct=us10y_latest,
            us10y_5d_change_bps=us10y_5d_change_bps,
            us10y_last_date=us10y_last_date,
            cpi_yoy_pct=self._cpi_yoy(cpi_series),
            cpi_prev_yoy_pct=self._cpi_prev_yoy(cpi_series),
            cpi_last_date=cpi_last_date,
            fear_greed_value=fear_greed_result[0] if fear_greed_result else None,
            fear_greed_label=fear_greed_result[1] if fear_greed_result else None,
            fear_greed_prev_value=fear_greed_result[2] if fear_greed_result else None,
            funding_rate_pct=funding_rate,
            fed_hawkish=self._manual_bool("fed_hawkish"),
            geopolitical_risk_up=self._manual_bool("geopolitical_risk_up"),
            semicon_export_usd_100m=semicon_result[0] if semicon_result else None,
            semicon_export_month=semicon_result[1] if semicon_result else None,
            semicon_export_prev_usd_100m=semicon_result[2] if semicon_result else None,
            semicon_export_prev_month=semicon_result[3] if semicon_result else None,
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

    def _get_fear_greed(self) -> tuple[int, str, int | None]:
        data = get_json(ALTERNATIVE_ME_FNG_URL, params={"limit": 2})
        entries = data.get("data", [])
        if not entries:
            raise ValueError("No data in Fear & Greed response")
        today = entries[0]
        value = today.get("value")
        label = today.get("value_classification", "")
        if value is None:
            raise ValueError("No value in Fear & Greed response")
        prev_value = int(entries[1].get("value")) if len(entries) >= 2 else None
        return int(value), label, prev_value

    def _get_funding_rate(self) -> float:
        data = get_json(BINANCE_PREMIUM_INDEX_URL, params={"symbol": "BTCUSDT"})
        rate = data.get("lastFundingRate")
        if rate is None:
            raise ValueError("No lastFundingRate in Binance response")
        return round(float(rate) * 100, 4)

    def _get_semiconductor_exports(self) -> tuple[float, str, float, str] | None:
        """
        Returns (curr_100m, curr_yyyymm, prev_100m, prev_yyyymm) from 관세청 API.
        Unit: 억달러 (100M USD). Requires KICS_API_KEY.
        """
        if not self.settings.kics_api_key:
            return None

        now = datetime.now(timezone.utc)
        # Build last 3 months to find 2 consecutive ones with published data
        months: list[str] = []
        y, m = now.year, now.month
        for _ in range(3):
            months.append(f"{y}{m:02d}")
            m -= 1
            if m == 0:
                m, y = 12, y - 1

        results: dict[str, float] = {}
        for yyyymm in months:
            payload = get_json(
                KICS_TRADE_STATS_URL,
                params={
                    "serviceKey": self.settings.kics_api_key,
                    "yyyyMm": yyyymm,
                    "hsSgn": "4",
                    "itemCd": _SEMICON_HS4,
                    "type": "json",
                },
            )
            items = payload.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            if isinstance(items, dict):
                items = [items]
            for item in items:
                raw = item.get("expDlr")
                if raw not in (None, "", "0", 0):
                    # API unit: 천달러 → 억달러
                    results[yyyymm] = round(float(raw) / 100_000, 1)
                    break

        available = sorted(results, reverse=True)
        if len(available) < 2:
            return None
        curr, prev = available[0], available[1]
        return results[curr], curr, results[prev], prev

    def _get_naver_series(self, market_code: str, fdtc: int, *, limit: int = 10) -> list[FredObservation]:
        """Fetch price series from Naver Finance. Returns chronological order (oldest-first)."""
        rows: list[FredObservation] = []
        for page in range(1, 4):
            params = {"marketindexCd": market_code, "fdtc": fdtc, "page": page}
            html = get_text(NAVER_WORLD_DAILY_URL, params=params, headers=_NAVER_HEADERS)
            page_rows = _parse_naver_price_table(html)
            rows.extend(page_rows)
            if len(rows) >= limit or not page_rows:
                break
        return list(reversed(rows[:limit]))

    def _get_us10y_series_treasury(self, *, limit: int = 10) -> list[FredObservation]:
        """Fetch US 10Y Treasury yield from Treasury.gov. No API key required."""
        now = datetime.now(timezone.utc)
        url = TREASURY_YIELD_CURVE_BASE.format(year=now.year)
        params = {
            "type": "daily_treasury_yield_curve",
            "field_tdr_date_value_month": f"{now.year}{now.month:02d}",
            "download": "true",
        }
        text = get_text(url, params=params)
        reader = csv.DictReader(StringIO(text))
        points: list[FredObservation] = []
        for row in reader:
            if len(points) >= limit:
                break
            date_str = row.get("Date", "").strip()
            value_str = row.get("10 Yr", "").strip()
            if not date_str or not value_str:
                continue
            try:
                date_iso = datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")
                points.append(FredObservation(date=date_iso, value=float(value_str)))
            except (ValueError, KeyError):
                continue
        return list(reversed(points))

    def _get_fred_series(self, series_id: str, *, limit: int) -> list[FredObservation]:
        if not self.settings.fred_api_key:
            return []

        payload = get_json(
            FRED_SERIES_URL,
            params={
                "series_id": series_id,
                "api_key": self.settings.fred_api_key,
                "file_type": "json",
                "sort_order": "desc",
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
        return list(reversed(points))[-limit:]

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
