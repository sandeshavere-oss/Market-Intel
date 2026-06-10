# Changelog: MARKET_INTEL Platform
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2.2.0] - 2026-06-10

### Added
*   **[UNKNOWN_SYMBOL_RECOVERY_REPORT.md](file:///D:/MARKET_INTEL/DOCUMENTATION/UNKNOWN_SYMBOL_RECOVERY_REPORT.md)**: Report on takeover event symbol recovery.
*   **[EVENT_TABLE_UNIFICATION_REPORT.md](file:///D:/MARKET_INTEL/DOCUMENTATION/EVENT_TABLE_UNIFICATION_REPORT.md)**: Audit and ranking of event source table overlaps.
*   **[SIGNAL_EXPANSION_IMPACT_REPORT.md](file:///D:/MARKET_INTEL/DOCUMENTATION/SIGNAL_EXPANSION_IMPACT_REPORT.md)**: Projection model for signal counts across scenarios A-D.
*   **[THEME_ALLOCATION_FEASIBILITY_REPORT.md](file:///D:/MARKET_INTEL/DOCUMENTATION/THEME_ALLOCATION_FEASIBILITY_REPORT.md)**: Feasibility study on sector theme allocations to constituent stocks (Hold).
*   **[ROI_PRIORITY_REPORT.md](file:///D:/MARKET_INTEL/DOCUMENTATION/ROI_PRIORITY_REPORT.md)**: Opportunity prioritization ranking.
*   **[POST_IMPLEMENTATION_SIGNAL_AUDIT.md](file:///D:/MARKET_INTEL/DOCUMENTATION/POST_IMPLEMENTATION_SIGNAL_AUDIT.md)**: Validation outcome report for unified signal engine.
*   **[update_unknown_symbols.py](file:///D:/MARKET_INTEL/scratch/update_unknown_symbols.py)**: One-off database migration script to resolve unknown company symbols.

### Changed
*   **[company_master.csv](file:///D:/MARKET_INTEL/MAPPINGS/company_master.csv)**: Appended 4 newly recovered BSE/NSE ticker symbols and aliases.
*   **[signal_engine.py](file:///D:/MARKET_INTEL/NEWS_ENGINE/signal_engine.py)**: Upgraded retrieval logic to use a unified UNION query over all three event source tables and deduplicate in Python.

## [2.1.0] - 2026-06-10

### Added
*   **[SIGNAL_COVERAGE_AUDIT.md](file:///D:/MARKET_INTEL/DOCUMENTATION/SIGNAL_COVERAGE_AUDIT.md)**: Signal coverage audit outlining pipeline conversions, event mapping errors, and ignored database segments.
*   **[SIGNAL_AUDIT_REPORT.md](file:///D:/MARKET_INTEL/DOCUMENTATION/SIGNAL_AUDIT_REPORT.md)**: Quantitative signal quality audit analyzing event signals, performance rates, and failure patterns.
*   **[GAP_ANALYSIS.md](file:///D:/MARKET_INTEL/DOCUMENTATION/GAP_ANALYSIS.md)**: Gap analysis and component registry auditing the 8 core signal validation modules.
*   **[PROJECT_AUDIT.md](file:///D:/MARKET_INTEL/DOCUMENTATION/PROJECT_AUDIT.md)**: Platform analysis audit file tracking directories, schemas, n8n workflows, and duplication risks.
*   **[DATABASE_SCHEMA.md](file:///D:/MARKET_INTEL/DOCUMENTATION/DATABASE_SCHEMA.md)**: Full database schema blueprint mapping all database table layouts, column configurations, keys, and foreign constraints.
*   **[PROJECT_STATUS.md](file:///D:/MARKET_INTEL/DOCUMENTATION/PROJECT_STATUS.md)**: Platform module checklists, completion percentages, and pending tasks.
*   **[SESSION_SUMMARY.md](file:///D:/MARKET_INTEL/DOCUMENTATION/SESSION_SUMMARY.md)**: Chronological changes log of execution runs, bug fixes, and verified outputs.
*   **[ARCHITECTURE.md](file:///D:/MARKET_INTEL/DOCUMENTATION/ARCHITECTURE.md)**: Visual architecture system layouts, database entities, workflow sequences, and signal flow diagrams.
*   **[DECISIONS.md](file:///D:/MARKET_INTEL/DOCUMENTATION/DECISIONS.md)**: Strategic decisions log tracking frozen themes, entry pricing, database splits, and fallback logic.
*   **[ROADMAP.md](file:///D:/MARKET_INTEL/DOCUMENTATION/ROADMAP.md)**: Completed sprint goals, future visions, ROI priorities, and risk registers.
*   **[migration.py](file:///D:/MARKET_INTEL/NEWS_ENGINE/migration.py)**: SQLite migration script to inject `source_timestamp` and `system_timestamp` into `keywords`.
*   **[price_loader.py](file:///D:/MARKET_INTEL/PRICE_ENGINE/price_loader.py)**: Daily incremental historical stock price loader using Yahoo Finance (`yfinance`).
*   **[validate_signals.py](file:///D:/MARKET_INTEL/SIGNAL_ENGINE/validate_signals.py)**: Quantitative backtest evaluator checking next-day trading opens and 5d/10d returns.

### Changed
*   **[price_data.db](file:///D:/MARKET_INTEL/DATABASE/price_data.db)**: Added `adj_close` column to `price_history` database table schema and synced legacy values.
*   **[market_intel.db](file:///D:/MARKET_INTEL/DATABASE/market_intel.db)**: Migrated `keywords` table columns to include `source_timestamp` and `system_timestamp`.
*   **[capture_rss.py](file:///D:/MARKET_INTEL/NEWS_ENGINE/capture_rss.py)**: Modified database insertion calls to write dual timestamps.
*   **[save_keywords.py](file:///D:/MARKET_INTEL/NEWS_ENGINE/save_keywords.py)**: Configured to support publication dates and local timestamps on insert.
*   **[enrich_news.py](file:///D:/MARKET_INTEL/NEWS_ENGINE/enrich_news.py)**: Commented to ensure preservation of dual timestamps.
*   **[dashboard.py](file:///D:/MARKET_INTEL/dashboard.py)**: Upgraded Streamlit tab layout to display 9 metrics (win rates, averages, best/worst) and the Recent Results table.
