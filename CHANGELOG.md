# Changelog: MARKET_INTEL Platform
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [3.0.0] - 2026-06-10

### Added
*   **[banner.png](file:///D:/MARKET_INTEL/docs/assets/banner.png)**: Investor-grade repository banner image.
*   **[PROJECT_OVERVIEW.md](file:///D:/MARKET_INTEL/docs/PROJECT_OVERVIEW.md)**: Detailed methodologies for company entity tracking, velocity spikes, and signal convergence.
*   **[DATA_PIPELINE.md](file:///D:/MARKET_INTEL/docs/DATA_PIPELINE.md)**: Documentation of ingestion poller, Playwright crawlers, local Ollama LLM enrichment, and backtesting.
*   **[DATABASE_SCHEMA.md](file:///D:/MARKET_INTEL/docs/DATABASE_SCHEMA.md)**: Complete column details and logical database ERD mapping.
*   **[CONTRIBUTING.md](file:///D:/MARKET_INTEL/CONTRIBUTING.md)**: Community standards, branch styling, and PR templates.
*   **[.github/ISSUE_TEMPLATE/bug_report.md](file:///D:/MARKET_INTEL/.github/ISSUE_TEMPLATE/bug_report.md)**: Template for reporting issues.
*   **[.github/ISSUE_TEMPLATE/feature_request.md](file:///D:/MARKET_INTEL/.github/ISSUE_TEMPLATE/feature_request.md)**: Template for pitching features.
*   **[.github/pull_request_template.md](file:///D:/MARKET_INTEL/.github/pull_request_template.md)**: Pull Request template.

### Changed
*   **[README.md](file:///D:/MARKET_INTEL/README.md)**: Complete overhaul with banners, badges, workflows, and installation guides.
*   **[MARKET_INTEL_ROADMAP.md](file:///D:/MARKET_INTEL/MARKET_INTEL_ROADMAP.md)**: Overhauled with a research paper blueprint and listed tech companies theme mapping.
*   **Directory Reorganization**:
    *   `/DATABASE` -> `/database`
    *   `/LOGS` -> `/logs`
    *   `/BACKUP` -> `/archive`
    *   `/DOCUMENTATION` -> `/docs`
    *   `/MAPPINGS` -> `/data/mappings`
    *   `/AUDIT` -> `/data/audit`
    *   `dashboard.py` -> `/dashboard/dashboard.py`
    *   `NEWS_ENGINE/`, `PRICE_ENGINE/`, `SIGNAL_ENGINE/`, `SOCIAL_ENGINE/`, `CORPORATE_ENGINE/` -> `/scripts/` subdirectories.
*   **Path Refactoring**: Refactored paths in 22 Python engine scripts and the dashboard to support nested script subfolders and lowercase database directory naming.

### Removed
*   Legacy `.gitkeep` placeholder files in obsolete directory roots (`docs/`, `filter/`, `keywords/`, `models/`, `output/`, `scraper/`).

---

## [2.2.0] - 2026-06-10

### Added
*   **[UNKNOWN_SYMBOL_RECOVERY_REPORT.md](file:///D:/MARKET_INTEL/docs/UNKNOWN_SYMBOL_RECOVERY_REPORT.md)**: Report on takeover event symbol recovery.
*   **[EVENT_TABLE_UNIFICATION_REPORT.md](file:///D:/MARKET_INTEL/docs/EVENT_TABLE_UNIFICATION_REPORT.md)**: Audit and ranking of event source table overlaps.
*   **[SIGNAL_EXPANSION_IMPACT_REPORT.md](file:///D:/MARKET_INTEL/docs/SIGNAL_EXPANSION_IMPACT_REPORT.md)**: Projection model for signal counts across scenarios A-D.
*   **[THEME_ALLOCATION_FEASIBILITY_REPORT.md](file:///D:/MARKET_INTEL/docs/THEME_ALLOCATION_FEASIBILITY_REPORT.md)**: Feasibility study on sector theme allocations to constituent stocks (Hold).
*   **[ROI_PRIORITY_REPORT.md](file:///D:/MARKET_INTEL/docs/ROI_PRIORITY_REPORT.md)**: Opportunity prioritization ranking.
*   **[POST_IMPLEMENTATION_SIGNAL_AUDIT.md](file:///D:/MARKET_INTEL/docs/POST_IMPLEMENTATION_SIGNAL_AUDIT.md)**: Validation outcome report for unified signal engine.
*   **[update_unknown_symbols.py](file:///D:/MARKET_INTEL/scratch/update_unknown_symbols.py)**: One-off database migration script to resolve unknown company symbols.

### Changed
*   **[company_master.csv](file:///D:/MARKET_INTEL/data/mappings/company_master.csv)**: Appended 4 newly recovered BSE/NSE ticker symbols and aliases.
*   **[signal_engine.py](file:///D:/MARKET_INTEL/scripts/news_engine/signal_engine.py)**: Upgraded retrieval logic to use a unified UNION query over all three event source tables and deduplicate in Python.

---

## [2.1.0] - 2026-06-10

### Added
*   **[SIGNAL_COVERAGE_AUDIT.md](file:///D:/MARKET_INTEL/docs/SIGNAL_COVERAGE_AUDIT.md)**: Signal coverage audit outlining pipeline conversions, event mapping errors, and ignored database segments.
*   **[SIGNAL_AUDIT_REPORT.md](file:///D:/MARKET_INTEL/docs/SIGNAL_AUDIT_REPORT.md)**: Quantitative signal quality audit analyzing event signals, performance rates, and failure patterns.
*   **[GAP_ANALYSIS.md](file:///D:/MARKET_INTEL/docs/GAP_ANALYSIS.md)**: Gap analysis and component registry auditing the 8 core signal validation modules.
*   **[PROJECT_AUDIT.md](file:///D:/MARKET_INTEL/docs/PROJECT_AUDIT.md)**: Platform analysis audit file tracking directories, schemas, n8n workflows, and duplication risks.
*   **[DATABASE_SCHEMA.md](file:///D:/MARKET_INTEL/docs/DATABASE_SCHEMA.md)**: Full database schema blueprint mapping all database table layouts, column configurations, keys, and foreign constraints.
*   **[PROJECT_STATUS.md](file:///D:/MARKET_INTEL/docs/PROJECT_STATUS.md)**: Platform module checklists, completion percentages, and pending tasks.
*   **[SESSION_SUMMARY.md](file:///D:/MARKET_INTEL/docs/SESSION_SUMMARY.md)**: Chronological changes log of execution runs, bug fixes, and verified outputs.
*   **[ARCHITECTURE.md](file:///D:/MARKET_INTEL/docs/ARCHITECTURE.md)**: Visual architecture system layouts, database entities, workflow sequences, and signal flow diagrams.
*   **[DECISIONS.md](file:///D:/MARKET_INTEL/docs/DECISIONS.md)**: Strategic decisions log tracking frozen themes, entry pricing, database splits, and fallback logic.
*   **[ROADMAP.md](file:///D:/MARKET_INTEL/docs/ROADMAP.md)**: Completed sprint goals, future visions, ROI priorities, and risk registers.
*   **[migration.py](file:///D:/MARKET_INTEL/scripts/news_engine/migration.py)**: SQLite migration script to inject `source_timestamp` and `system_timestamp` into `keywords`.
*   **[price_loader.py](file:///D:/MARKET_INTEL/scripts/price_engine/price_loader.py)**: Daily incremental historical stock price loader using Yahoo Finance (`yfinance`).
*   **[validate_signals.py](file:///D:/MARKET_INTEL/scripts/signal_engine/validate_signals.py)**: Quantitative backtest evaluator checking next-day trading opens and 5d/10d returns.

### Changed
*   **[price_data.db](file:///D:/MARKET_INTEL/database/price_data.db)**: Added `adj_close` column to `price_history` database table schema and synced legacy values.
*   **[market_intel.db](file:///D:/MARKET_INTEL/database/market_intel.db)**: Migrated `keywords` table columns to include `source_timestamp` and `system_timestamp`.
*   **[capture_rss.py](file:///D:/MARKET_INTEL/scripts/news_engine/capture_rss.py)**: Modified database insertion calls to write dual timestamps.
*   **[save_keywords.py](file:///D:/MARKET_INTEL/scripts/news_engine/save_keywords.py)**: Configured to support publication dates and local timestamps on insert.
*   **[enrich_news.py](file:///D:/MARKET_INTEL/scripts/news_engine/enrich_news.py)**: Commented to ensure preservation of dual timestamps.
*   **[dashboard.py](file:///D:/MARKET_INTEL/dashboard/dashboard.py)**: Upgraded Streamlit tab layout to display 9 metrics (win rates, averages, best/worst) and the Recent Results table.
