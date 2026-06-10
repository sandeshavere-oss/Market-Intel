# Gap Analysis & System Audit: MARKET_INTEL

**Prepared by:** Quantitative Systems Auditor  
**Date:** June 10, 2026  
**Status:** Completed  

This document logs the technical audit of the `MARKET_INTEL` platform's signal validation and database components, identifying active implementations, functional verification, and system gaps.

---

## 1. Component Audit Registry

| Component | Target File / Database Table | Status | Verification & Functional Details |
| :--- | :--- | :--- | :--- |
| **1. price_data.db** | `d:/MARKET_INTEL/DATABASE/price_data.db` | **EXISTS** | SQLite database exists (size: ~8.2 MB). Operating in WAL journal mode for optimal concurrent read/write transactions. |
| **2. price_history table** | `price_history` inside `price_data.db` | **EXISTS** | Table is fully defined with columns `symbol`, `date` (PRIMARY KEY), `open`, `high`, `low`, `close`, `adj_close`, `volume`, and `created_at`. Contains 39,720 rows. |
| **3. price_loader.py** | `d:/MARKET_INTEL/PRICE_ENGINE/price_loader.py` | **EXISTS** | **Functional**: Uses `yfinance` to download daily prices incrementally. Includes MultiIndex checks and fallback to `'Close'` if `'Adj Close'` is absent. Verified running and successfully updating 259 records. |
| **4. validate_signals.py** | `d:/MARKET_INTEL/SIGNAL_ENGINE/validate_signals.py` | **EXISTS** | **Functional**: Runs backtesting holding returns (5d and 10d) starting from next-day Open to avoid look-ahead bias. Verified executing without syntax or database errors. |
| **5. signal_performance population** | `signal_performance` table in `market_intel.db` | **EXISTS** | **Functional**: Table contains computed stats for `TCS` signals (ID 4: LOSS, ID 5: PENDING). Signal ID 6 for `RELIANCE` is correctly skipped/pending since no price data exists post signal date (June 9, 2026). |
| **6. signal performance dashboard** | `d:/MARKET_INTEL/dashboard.py` | **EXISTS** | **Functional**: The Streamlit dashboard file reads directly from `signal_performance` in `market_intel.db` under `tab_performance`, rendering win rates, best/worst trades, and recent results. |
| **7. timestamp columns** | `source_timestamp` and `system_timestamp` in `keywords` table | **EXISTS** | **Functional**: Columns exist in `market_intel.db` and are successfully written during RSS crawls to monitor data latency. |
| **8. migration scripts** | `d:/MARKET_INTEL/NEWS_ENGINE/migration.py` | **EXISTS** | **Functional**: Python script checks the `keywords` table columns and runs SQLite `ALTER TABLE` statements to inject missing timestamp columns. |

---

## 2. Identified Gaps

### Gap 1: Absence of Benchmark-Relative Return Normalization [Risk: HIGH]
*   **Description:** Currently, `validate_signals.py` computes absolute returns. In a general market uptrend, absolute returns will appear positive even if the stock underperforms the index.
*   **Impact:** The system cannot prove if its convergence signals generate true **Alpha ($\alpha$)** or are simply riding beta momentum.
*   **Required Action:** Modify the price loader and validator to download Nifty 50 index prices (`^NSEI`) and subtract matching-period index returns from the stock returns.

### Gap 2: Synchronous Local LLM Processing Queue [Risk: MEDIUM]
*   **Description:** AI text enrichment (`enrich_news.py`) using the local Ollama Mistral model is executed synchronously inside n8n pipelines.
*   **Impact:** A burst of RSS articles causes n8n script execution blocks, which can lead to network timeouts and ingestion drops.
*   **Required Action:** Build a database-backed job queue to decouple quick article captures from high-latency LLM analysis.

### Gap 3: Codebase Redundancies & Technical Debt [Risk: LOW]
*   **Description:** Legacy files from older engines remain in the workspace.
    *   `NEWS_ENGINE/price_history_loader.py` and `NEWS_ENGINE/price_engine.py` are duplicates of `PRICE_ENGINE/price_loader.py`.
    *   `NEWS_ENGINE/signal_engine.py` and `NEWS_ENGINE/performance_tracker.py` are duplicates of `SIGNAL_ENGINE/validate_signals.py`.
*   **Impact:** Risk of developer confusion and incorrect imports.
*   **Required Action:** Archive and delete duplicate files.

### Gap 4: Hardcoded Absolute Directory Paths [Risk: LOW]
*   **Description:** Multiple scripts utilize absolute paths (e.g. `D:/MARKET_INTEL/...`).
*   **Impact:** Platform fails to run if migrated to a different drive letter or server environment.
*   **Required Action:** Replace absolute path strings with dynamic paths resolved using `pathlib.Path(__file__)`.
