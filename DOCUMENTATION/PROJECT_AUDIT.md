# Comprehensive Project Audit: MARKET_INTEL
**Prepared by:** Permanent Project Director & Technical Architect  
**Date:** June 10, 2026  
**Status:** Completed

This document provides a complete audit of the `MARKET_INTEL` project, detailing code structures, databases, schemas, and features to ensure project files and the NotebookLM knowledge base are synchronized.

---

## 1. Current Architecture

The platform is designed around a multi-tier pipeline transitioning from **News Intelligence** to a **Validated Signal Intelligence Platform**.

1.  **Ingestion Tier:** Captures articles from news RSS feeds, scheduled board meetings from BSE filing notices, and tweets from target social media handles.
2.  **AI Analysis Tier:** Tags keywords, identifies related stock tickers, classifies articles into standard themes, and extracts sentiment/impact metrics using local LLM models (Ollama Mistral:7b).
3.  **Analytics & Signal Tier:** Aggregates daily mentions, evaluates theme momentum (Z-Scores/velocities), and triggers convergence signals when mention spikes coincide with upcoming board meetings.
4.  **Backtest Validation Tier:** Fetches price history incrementally from Yahoo Finance and calculates forward returns over 5-day and 10-day holds to classify signals as WIN, LOSS, or NEUTRAL.
5.  **Presentation Tier:** Renders metrics, timelines, briefings, feeds, and backtesting tables on a glassmorphic Streamlit web dashboard.

---

## 2. Folder Structure

The repository is structured logically to separate engines, mappings, databases, and logs:

```text
D:/MARKET_INTEL/
├── .env                              # API keys, database paths, and environment settings
├── dashboard.py                      # Main Streamlit web dashboard app
├── MARKET_INTEL_ROADMAP.md           # Root level roadmap reference
├── AUDIT/                            # CSVs listing unclassified articles for manual review
├── BACKUP/                           # Historical code configuration backups
├── CORPORATE_ENGINE/                 # BSE parsing and corporate filings logic
│   └── save_corp_data.py
├── DATABASE/                         # SQLite databases
│   ├── market_intel.db
│   ├── price_data.db
│   ├── corporate_events.db
│   └── twitter_intel.db
├── DOCUMENTATION/                    # Centralized knowledge base
│   ├── ARCHITECTURE.md
│   ├── CHANGELOG.md
│   ├── DATABASE_SCHEMA.md
│   ├── DECISIONS.md
│   ├── PROJECT_AUDIT.md
│   ├── PROJECT_STATUS.md
│   ├── ROADMAP.md
│   └── SESSION_SUMMARY.md
├── LOGS/                             # Runtime log files
├── MAPPINGS/                         # Company ticker and theme mapping dictionaries
│   ├── company_master.csv
│   └── theme_mappings.csv
├── NEWS_ENGINE/                      # Ingestion, keyword parsing, and LLM enrichment scripts
│   ├── capture_rss.py
│   ├── company_match.py
│   ├── enrich_news.py
│   ├── migration.py
│   └── save_keywords.py
├── PRICE_ENGINE/                     # Historical price sync scripts
│   └── price_loader.py
├── SIGNAL_ENGINE/                    # Signal calculation and outcome validator scripts
│   └── validate_signals.py
├── SOCIAL_ENGINE/                    # Social media playwright scraping scripts
│   └── save_tweets.py
└── WORKFLOWS/                        # n8n workflow JSON blueprints
```

---

## 3. Databases

The system coordinates four SQLite databases to prevent locks and optimize read/write concurrency:

1.  `market_intel.db`: Stores article records, daily aggregate mentions, theme velocities, and convergence signal logs.
2.  `price_data.db`: Stores daily historical stock price bars for constituents.
3.  `corporate_events.db`: Tracks official corporate disclosures, schedule meetings, and earnings reports.
4.  `twitter_intel.db`: Contains ingested tweets, handles, and basic sentiment scores.

---

## 4. Database Schemas

Schemas have been standardized to support strict relational integrity and backtesting requirements:

*   **`keywords` (`market_intel.db`):** Includes `source_timestamp` (publication time) and `system_timestamp` (write time) to track ingestion latency.
*   **`price_history` (`price_data.db`):** Contains `adj_close` (adjusted close price) to prevent dividends/splits from skewing returns.
*   **`signal_performance` (`market_intel.db`):** Uses a primary key `signal_id` which acts as a foreign key referencing `event_signals(id)`. Stores entry opens, exit closes, returns, and outcomes.
*   **`board_meetings` & `financial_results` (`corporate_events.db`):** Stores upcoming schedules and earnings reports.

*(For full column types and keys, see `DOCUMENTATION/DATABASE_SCHEMA.md`)*

---

## 5. Workflows

Operational workflows are mapped using n8n JSON configs (`WORKFLOWS/`):
*   `capture_workflow.json`: Triggers RSS capture crons.
*   `enrichment_workflow.json`: Calls `enrich_news.py` to classify and tag raw articles.
*   `bse_ingestion.json`: Runs notice crawlers and extracts upcoming meeting schedules.
*   `twitter_ingestion.json`: Controls Playwright scraping sequences.

---

## 6. Active Features

*   **Dual Ingestion Timestamps:** Ingested articles save publication dates and local write dates.
*   **Adjusted Close Synchronization:** Daily prices download splitting/dividend-adjusted closes incrementally.
*   **Realistic Entry-Exit Validation:** Returns are calculated using next-day Open to prevent look-ahead bias.
*   **Performance Metrics Dashboard:** Streamlit UI displays total signals, win rates, averages, and best/worst trades.
*   **Frozen Theme Velocity:** 16 standard themes are tracked to prevent categorization loops.

---

## 7. Incomplete Features

*   **Benchmark Relative Returns (Nifty 50 Adjustments):** Currently, returns are absolute. Evaluating index-relative returns is planned for the next sprint.
*   **Asynchronous Processing Queue:** A queue to decouple slow Ollama LLM requests from fast RSS ingestions.

---

## 8. Broken Features

*   *None currently.* Playwright crawler sessions are stable but require cookie refresh intervals.

---

## 9. Technical Debt

*   **Duplicate Price Loaders:** Legacy files `NEWS_ENGINE/price_history_loader.py` and `NEWS_ENGINE/price_engine.py` are deprecated in favor of `PRICE_ENGINE/price_loader.py` but remain in the repository.
*   **Duplicate Signal Calculators:** `NEWS_ENGINE/signal_engine.py` and `NEWS_ENGINE/performance_tracker.py` are deprecated in favor of `SIGNAL_ENGINE/validate_signals.py`.
*   **Hardcoded File Paths:** Some scripts use absolute paths (e.g., `D:/MARKET_INTEL/...`) instead of dynamic path-resolution (`Path(__file__).resolve()`).

---

## 10. Recommended Next Steps

1.  **Delete Deprecated Code:** Safely archive and remove deprecated scripts in `NEWS_ENGINE/` to clear clutter.
2.  **Relative Return Normalization:** Modify `validate_signals.py` to compare stock returns against Nifty 50 returns for identical dates.
3.  **LLM Queue Implementation:** Introduce a SQLite table-backed job queue for LLM enrichments to prevent n8n script timeouts.
