# Current Progress Report: MARKET_INTEL

This report highlights the active features, development checklist, and completed milestones of the `MARKET_INTEL` platform.

---

## 1. Development Progress Checklist

*   **Ingestion & Collection Layer:** `100% Complete`
    *   [x] RSS News Feed Poller (captures raw articles into `keywords`)
    *   [x] BSE Notice Playwright Crawler (extracts official notices and schedules)
    *   [x] Twitter Quant Handles Scraper (Playwright scraper using cookie logins)
    *   [x] Ingestion Latency Tracking (records dual timestamps `source_timestamp` and `system_timestamp`)
*   **Classification Layer:** `100% Complete`
    *   [x] Local LLM News Enrichment (sentiment, impact, and entity extraction via Ollama Mistral:7b)
    *   [x] Frozen Theme Mapping (strictly maps categories to 16 locked themes to prevent loop drift)
    *   [x] Company Name Ticker Mapping (maps company mentions to exchange tickers using master CSV)
*   **Signal Layer:** `100% Complete`
    *   [x] Mention Velocity Engine (calculates 7d/30d average volume and computes Z-Scores)
    *   [x] Board Meeting Convergence (generates signal when Z-Score > 2.5x and board meeting occurs in 7 days)
*   **Validation Layer:** `90% Complete`
    *   [x] Incremental Price Loader (fetches daily OHLCV and Adjusted Close via Yahoo Finance)
    *   [x] Realistic Entry pricing (sets entry price to next-day Open to eliminate look-ahead bias)
    *   [x] Absolute Returns calculation (calculates 5-day and 10-day holding returns using Adjusted Close)
    *   [ ] Benchmark relative returns normalization (planned for current sprint)
*   **Presentation Layer:** `100% Complete`
    *   [x] Streamlit Glassmorphic Dashboard (displays metrics: total signals, win rate, best/worst trades, and signal history grid)

---

## 2. Recent Upgrades & Release (v2.1.0)
The platform was recently upgraded from a basic news classification board to a quantitative signal validator. Key updates:
1.  **Adjusted Close Implementation:** Re-aligned `price_history` to support splitting/dividend-adjusted close prices, correcting false losses from corporate action gaps.
2.  **Next-Day Open Entry:** Shifted entry price evaluations from closing price of signal date to next-day Open, ensuring backtest signals can be executed in real trading.
3.  **9-Metric Dashboard Layout:** Enhanced Streamlit dashboard to show win rates, total win/loss, average return percentages, best and worst signals, and pending trackers.
4.  **Database Decoupling:** Separated one main SQLite file into four specialized databases (`market_intel.db`, `price_data.db`, `corporate_events.db`, `twitter_intel.db`) to remove file-locking conflicts.
5.  **Audit Logs:** Added unmapped keyword/theme capture outputs in `AUDIT/` for manual dictionary refining.
