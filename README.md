# BTC Macro Slack Reporter

Daily BTC macro scorecard that runs on GitHub Actions and posts a Slack report.

## What it does

- Pulls BTC spot and a weekly close proxy from CoinGecko.
- Pulls WTI, US 10Y, and CPI data from FRED.
- Pulls spot BTC ETF net flow from Farside when available.
- Applies a rules-based scoring model first.
- Optionally asks an LLM to turn the scored output into a short narrative.
- Sends the final report to Slack.

## Scoring model

Current first-pass rules:

- Oil 5-day average `<= 90`: `+1`
- Oil spot `>= 100`: `-2`
- ETF net inflow `> 0`: `+2`
- ETF net outflow `< 0`: `-2`
- US 10Y 5-day change `<= -5bps`: `+1`
- Fed hawkish manual flag: `-2`
- CPI cooling versus previous monthly print: `+2`
- Geopolitical risk manual flag: `-2`
- BTC weekly close proxy `> 126k`: `+2`

Interpretation thresholds:

- Score `>= 3`: `bullish`
- Score `<= -3`: `risk-off`
- Otherwise: `neutral`

## Required accounts and API keys

### Slack

Create a Slack app, install it to the workspace, and grant at least:

- `chat:write`

Then capture:

- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_ID`

### FRED

Create an API key and store it as:

- `FRED_API_KEY`

### OpenAI (optional)

Only needed if you want the LLM-written narrative:

- `OPENAI_API_KEY`

## Repository secrets and variables

Set these GitHub Secrets:

- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_ID`
- `FRED_API_KEY`
- `OPENAI_API_KEY` (optional)

Set these GitHub Variables if you want to tune thresholds without code changes:

- `OPENAI_MODEL`
- `USE_LLM_SUMMARY`
- `WEEKLY_BREAKOUT_THRESHOLD`
- `OIL_STABLE_THRESHOLD`
- `OIL_RISK_THRESHOLD`
- `ETF_POSITIVE_THRESHOLD`
- `ETF_NEGATIVE_THRESHOLD`
- `TEN_YEAR_CHANGE_THRESHOLD_BPS`
- `CPI_COOLING_THRESHOLD`
- `SCORE_BULL_THRESHOLD`
- `SCORE_RISK_THRESHOLD`

## Schedule

The workflow runs at `01:17 UTC`, which is `10:17 KST`.

File: [daily-report.yml](/f:/개인/btc-report/.github/workflows/daily-report.yml)

## Local development

1. Create `.env` from `.env.example`.
2. Optionally create `data/manual_context.json` from `data/manual_context.example.json`.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Dry run:

```bash
python -m app.main --dry-run
```

## Manual context

Some signals are intentionally left as manual overrides in `data/manual_context.json` because they are hard to define cleanly without a news classification pipeline:

- `fed_hawkish`
- `geopolitical_risk_up`
- `notes`

That keeps the scoring layer deterministic while you decide how you want to automate those inputs later.

## Recommended next step

Replace the manual flags with one of these:

- A news ingestion step plus keyword or classifier scoring
- A separate curated JSON file updated by you
- An LLM classifier that only outputs structured booleans before the final narrative step
