# Feature Status Board: MARKET_INTEL
**Version:** 4.0.0  
**Last Checked:** June 13, 2026

This status board tracks the development progression of the `MARKET_INTEL` platform modules.

---

## 1. Core Layer Metrics

*   **Collection Layer:** 100%
*   **Classification Layer:** 100%
*   **Signal Layer:** 100%
*   **Knowledge Graph Propagation:** 100%
*   **Options Integration Layer:** 100%
*   **Validation Layer:** 100%
*   **Overall Project Progress:** 100%

---

## 2. Feature Status Directory

### A. Ingestion & Collection Layer
*   **RSS News Feed Poller:** `COMPLETED` (100%) - Automatic RSS pulls storing raw articles.
*   **BSE filing Notice Crawler:** `COMPLETED` (100%) - Playwright crawler extracting announcements.
*   **Twitter Pulse Scraper:** `COMPLETED` (100%) - Scrapes targeted quant handles via browser session cookies.
*   **Dual Ingestion Timestamps:** `COMPLETED` (100%) - Captures `source_timestamp` and `system_timestamp`.

### B. Classification Layer
*   **Local LLM News Enrichment:** `COMPLETED` (100%) - Extracts entities and sentiment using local Ollama model.
*   **Frozen Theme Mapping:** `COMPLETED` (100%) - Restricts categorization to 16 core themes to prevent loop drift.
*   **Company Name Ticker Mapping:** `COMPLETED` (100%) - Resolves company mentions to standard exchange symbols.

### C. Signal Layer
*   **Mention Velocity Engine:** `COMPLETED` (100%) - Calculates spike ratios against 30-day averages.
*   **Board Meeting Convergence:** `COMPLETED` (100%) - Registers signals when velocity spikes overlap with scheduled board meetings.
*   **Unknown Symbol Recovery:** `COMPLETED` (100%) - Mapped and recovered 4 takeover events from 'Unknown' to resolved tickers.
*   **Event Table Unification:** `COMPLETED` (100%) - Updated signal engine to query corporate_events, board_meetings, and financial_results using a UNION query.
*   **Market Impact Propagation Engine (v4.0):** `COMPLETED` (100%) - Traverses multi-order upstream/downstream nodes through a seeded Knowledge Graph.

### D. Validation Layer
*   **Incremental Price Syncer:** `COMPLETED` (100%) - Daily Yahoo Finance sync with `adj_close` support.
*   **Backtest Return Engine:** `COMPLETED` (100%) - Calculates 5d/10d returns using next-day Open to eliminate look-ahead bias.
*   **Benchmark Relative Returns:** `IN PROGRESS` (50%) - Normalizing returns against matching Nifty 50 performance to isolate alpha.
*   **Options Chain Scraper & Greeks Engine:** `COMPLETED` (100%) - Scrapes NSE chain via API v3 (headful mode bypass) and calculates standard Greeks and IV Percentiles.
*   **Options Rebalanced Scoring (v2.1):** `COMPLETED` (100%) - Factors in PCR and OI Skew, and applies Pre-Event IV Reversal Penalties.

### E. Deprecated Features
*   **Legacy Price loaders (`NEWS_ENGINE/price_history_loader.py`, `price_engine.py`):** `DEPRECATED` (0%) - Replaced by `PRICE_ENGINE/price_loader.py`.
*   **Legacy Signal Engines (`NEWS_ENGINE/signal_engine.py`, `performance_tracker.py`):** `DEPRECATED` (0%) - Replaced by `SIGNAL_ENGINE/validate_signals.py`.

---

## 3. Platform Risks Registry

### Playwright Ingestion Session Blocks [Risk: HIGH]
*   **Impact:** Twitter crawls fail if login sessions expire or are blocked by CAPTCHA.
*   **Mitigation:** Configured local cookie loader script and logged recovery workflow.

### Local Ollama Pipeline Lag [Risk: MEDIUM]
*   **Impact:** Running LLM queries synchronously can stall the news poller execution.
*   **Mitigation:** n8n scripts run asynchronously; planned job queue decoupling in next sprint.

### Post-Event Volatility Crush (Vega Decay) [Risk: HIGH]
*   **Impact:** Buying call options on a high-conviction event signal right before the event results in severe loss due to implied volatility collapse.
*   **Mitigation:** `MITIGATED` (100%) - Implemented the Pre-Event IV Reversal Penalty in Signal Score v2.1 to demote signals with elevated option premiums.
