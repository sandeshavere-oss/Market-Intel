# Strategic Roadmap: MARKET_INTEL

This document outlines the milestones, sprin goals, risk metrics, and future development vision for the `MARKET_INTEL` platform.

---

## 1. Completed Milestones

### Ingestion & Analysis Foundation
*   **RSS & Notice Capture Pipelines:** Deployed Playwright BSE notification crawlers and RSS feed pollers.
*   **AI Enrichment & Classification:** Integrated local Ollama Mistral:7b model to extract keywords, sentiments, and impact levels.
*   **Frozen Theme Mapping:** Standardized keyword matches to a locked list of 16 structural market themes to prevent expansion loops.

### Validated Signal Transition
*   **Price Engine (Phase 1):** Migrated SQLite `price_history` schema, added `adj_close` column, and backfilled Yahoo Finance historical price logs.
*   **Ingestion Timestamps (Phase 2):** Injected dual timestamps (`source_timestamp` and `system_timestamp`) into raw keywords table to measure latency.
*   **Signal Validator (Phase 3):** Developed backtesting engine that uses next-day Open prices as trade entry and calculates 5-day and 10-day holds using adjusted Close.
*   **Dashboard Overhaul (Phase 4):** Revamped Streamlit Signal Performance tab with a 9-metric grid and a clean recent results layout.
### Signal Expansion & Data Quality (Version 2.2.0)
*   **Unknown Symbol Recovery (Phase 6.1):** Recovered 100% of 'Unknown' takeover events, mapped tickers in SQLite, and expanded `company_master.csv`.
*   **Event Table Unification (Phase 6.2):** Unified `corporate_events`, `board_meetings`, and `financial_results` tables using SQL UNION and Python deduplication.
*   **Post-Implementation Validation (Phase 7):** Validated historical signal consistency and verified zero regression.
### Market Impact & Options Layer (v4.0.0)
*   **Knowledge Graph (Phase 8.1):** Deployed directed graph schemas, traversal, sign propagation, and depth-based decay.
*   **Options Greeks Layer (Phase 8.2):** Built options chain scraper, Black-Scholes Greeks calculators, and IV percentile calculators in `price_data.db`.
*   **Signal Score v2.1 (Phase 8.3):** Rebalanced weights to include PCR/OI Skew (10%) and IV Reversal Penalty (15-point event bonus discount under high IV).

---

## 2. Current Sprint

*   **Benchmark Relative Returns:**
    *   Integrate Nifty 50 relative return adjustments ($\alpha$ calculations) into `validate_signals.py`.
*   **Blind Out-of-Sample Testing:**
    *   Run a 30-day forward test on live F&O names using the v2.1 scoring formula.

---

## 3. Next Sprint

*   **LLM Decoupling Queue:**
    *   Develop a lightweight SQLite-based job queue to separate news capturing from high-latency LLM processing.
*   **Automatic Relation Extraction:**
    *   Train/prompt local LLM to dynamically output new nodes/edges from incoming articles for automatic graph expansion.

---

## 4. Future Vision

*   **Sentiment-Adjusted Sizing:** Construct an automated position-sizing algorithm that scales exposure based on LLM conviction and Twitter mention velocity.
*   **Mid-Cap Expansion:** Scale price history capture to include the Nifty Midcap 100 universe.
*   **Paper Trading API Connector:** Create a notifier hook to send signal executions to a simulated broker account or messaging app (Telegram/Slack).

---

## 5. Blocked Tasks
*   *None currently.* Ollama processing times are a minor throughput bottleneck, but not blocking.

---

## 6. Highest ROI Task

### Benchmark-Relative Return Normalization
*   **Description:** Adjusting returns against Nifty 50.
*   **Why:** Currently, absolute returns can look positive during bull markets even if the signal underperforms the index. Normalizing against the index answers the critical question: *"Can this system generate signals that outperform the market?"*

---

## 7. Highest Risk Task

### Twitter Ingestion Reliability
*   **Description:** Maintaining Playwright-based X (Twitter) crawls.
*   **Why:** Standard Twitter web scraping is highly sensitive to UI changes, account blocks, cookie expirations, and IP rate-limiting. A session failure in the crawler silently freezes the Social Pulse tab.
*   **Mitigation:** Transition to official API hooks where feasible or integrate robust cookie rotation and proxy-switching libraries.
