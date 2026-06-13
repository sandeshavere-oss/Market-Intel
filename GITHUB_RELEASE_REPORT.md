# GitHub Release Report: MARKET_INTEL v4.0

**Release Tag/Version:** v4.0.0  
**Commit Message:** `MARKET_INTEL v4.0 - Impact Propagation Engine + Options Layer Integration`  
**Commit Hash:** `d6e2074`  
**Push Status:** `SUCCESSFUL` (Pushed to branch `main` at `https://github.com/sandeshavere-oss/Market-Intel`)  
**Release Date:** June 13, 2026

---

## 1. Files Changed

The following existing files were modified and committed in this release:
1.  **`CHANGELOG.md`** & **`docs/CHANGELOG.md`**: Updated release logs to record v4.0.0.
2.  **`docs/PROJECT_STATUS.md`**: Updated metrics, layer checklists, and risks registry to 100% completion for v4.0.0.
3.  **`docs/ARCHITECTURE.md`**: Updated System Architecture and Relational ERD diagrams.
4.  **`docs/ROADMAP.md`**: Updated Completed Milestones, Current Sprint, and Next Sprint targets.
5.  **`docs/EXECUTIVE_SUMMARY.md`**: Overhauled pipeline layer descriptions to incorporate Knowledge Graph and Options Greeks.
6.  **`docs/CURRENT_PROGRESS_REPORT.md`**: Updated development progress checklists and recent upgrade logs.
7.  **`docs/DATABASE_SCHEMA.md`**: Added detailed table schemas for the 5 new tables.

---

## 2. Files Added

The following new files were created and committed in this release:

### Documentation
1.  **`DOCUMENTATION/MARKET_INTEL_V4_IMPACT_ENGINE_REPORT.md`**: Master change report detailing engine logic and scenario outcomes.
2.  **`DOCUMENTATION/ALEX_REVIEW_PACKAGE.md`**: Independent project review package.
3.  **`options_layer_notes.md`**: Option Greeks layer integration design document.
4.  **`signal_v2.1_notes.md`**: Rebalanced weights, mathematical formulas, and backtest logs for Signal v2.1.
5.  **`docs/MISSED_SIGNAL_ANALYSIS.md`**: Audit of missed signal classes and precision improvement.
6.  **`docs/MONITORING_ARCHITECTURE.md`**: System health and performance monitoring documentation.
7.  **`docs/POST_EXPANSION_SIGNAL_AUDIT.md`**: Quantitative evaluation of signal expansion precision.

### Scripts & Schemas
8.  **`scripts/news_engine/impact_engine.py`**: Core graph traversal, decay, and direction-flipping engine.
9.  **`scripts/news_engine/impact_schema_migration.py`**: Schema builder and seeding script for the Knowledge Graph.
10. **`scripts/news_engine/test_impact_scenarios.py`**: Integration testing script for the 5 macro scenarios.
11. **`scripts/news_engine/check_processed.py`**: Processing state audit script.
12. **`scripts/news_engine/unconverged_signal_engine.py`**: Handles standalone thematic momentum signals.
13. **`scripts/price_engine/options_schema_migration.py`**: Schema builder for options data structures.
14. **`scripts/price_engine/options_chain_scraper.py`**: Playwright scraper for NSE Option Chains.
15. **`scripts/price_engine/compute_greeks.py`**: Computes Black-Scholes Greeks and relative IV percentiles.
16. **`scripts/price_engine/backtest_signals_v2_1.py`**: Scoring v2.1 backtest runner over 83 signals.
17. **`scripts/price_engine/compare_reliance_snapshots.py`**: Pre- vs. Post-event live options comparison.
18. **`scripts/price_engine/export_reliance_snapshot.py`**: Snapshot utility for options data.
