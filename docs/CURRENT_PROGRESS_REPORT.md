# Current Progress Report: MARKET_INTEL

This report highlights the active features, development checklist, and completed milestones of the `MARKET_INTEL` platform.

---

## 1. Development Progress Checklist

*   **Ingestion & Collection Layer:** `100% Complete`
    *   [x] RSS News Feed Poller (captures raw articles into `keywords`)
    *   [x] BSE Notice Playwright Crawler (extracts official notices and schedules)
    *   [x] Twitter Quant Handles Scraper (Playwright scraper using cookie logins)
    *   [x] Ingestion Latency Tracking (records dual timestamps `source_timestamp` and `system_timestamp`)
    *   [x] Options Chain Scraper (headful Chromium bypass of NSE anti-bot controls)
*   **Classification Layer:** `100% Complete`
    *   [x] Local LLM News Enrichment (sentiment, impact, and entity extraction via Ollama Mistral:7b)
    *   [x] Frozen Theme Mapping (strictly maps categories to 16 locked themes to prevent loop drift)
    *   [x] Company Name Ticker Mapping (maps company mentions to exchange tickers using master CSV)
*   **Knowledge Graph Layer:** `100% Complete`
    *   [x] Systemic Impact Propagation Traversal (DFS with sign propagation and depth-based decay)
    *   [x] Knowledge Graph Seeding (seeds baseline nodes and edges in `market_intel.db`)
*   **Options Integration Layer:** `100% Complete`
    *   [x] Options DB Migrations (creates `options_chain` and `options_summary` tables in `price_data.db`)
    *   [x] Greeks Engine (computes Black-Scholes Delta, Gamma, Theta, Vega, and IV Percentiles)
*   **Signal Layer:** `100% Complete`
    *   [x] Mention Velocity Engine (calculates 7d/30d average volume and computes Z-Scores)
    *   [x] Board Meeting Convergence (generates signal when Z-Score > 2.5x and board meeting occurs in 7 days)
    *   [x] Signal Score v2.1 Scoring Model (rebalanced weights to include 10% options component)
    *   [x] Pre-Event IV Reversal Penalty (Vega crush risk discount)
*   **Validation Layer:** `95% Complete`
    *   [x] Incremental Price Loader (fetches daily OHLCV and Adjusted Close via Yahoo Finance)
    *   [x] Realistic Entry pricing (sets entry price to next-day Open to eliminate look-ahead bias)
    *   [x] Absolute Returns calculation (calculates 5-day and 10-day holding returns using Adjusted Close)
    *   [ ] Benchmark relative returns normalization (In Progress)
*   **Presentation Layer:** `100% Complete`
    *   [x] Streamlit Glassmorphic Dashboard (displays metrics: total signals, win rate, best/worst trades, and signal history grid)

---

## 2. Recent Upgrades & Release (v4.0.0)
The platform has been upgraded from a basic event convergence engine to a market impact propagation engine with derivatives-based sentiment checking:
1.  **Market Impact Propagation Engine (v4.0):** Traces news events through a Knowledge Graph of sectors, suppliers, and competitors.
2.  **Options Chain Scraping & Greeks Calculations:** Scrapes NSE Option Chains using headful Playwright browsers and calculates Greeks (Delta, Gamma, Vega, Theta) alongside relative IV Percentiles.
3.  **Signal v2.1 Scoring Weight Rebalancing:** Rebalanced scoring weights to allocate 10% to options positioning (PCR & OI Skew) and applied a pre-event IV penalty to mitigate Vega crush risk.
4.  **83-Signal Backtest Validation:** Evaluated and verified performance improvements against 83 historical candidates, demoting 2 loss-making reversals (TCS) and surfacing profitable alpha (RECLTD +5.17%).
