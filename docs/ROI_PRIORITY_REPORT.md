# ROI Priority Report: MARKET_INTEL

**Prepared by:** Lead Systems Architect & Project Director  
**Date:** June 10, 2026  
**Status:** Completed  

This report evaluates and ranks the five signal coverage expansion opportunities by effort, risk, and expected signal/data quality returns to establish the execution priority.

---

## 1. Opportunity Ranking Matrix

| Rank | Opportunity | Effort | Risk | Signal Yield (Historical) | Signal Yield (Future / Live) | Data Quality Improvement | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Unknown Symbol Recovery** | **Low** | **Low** | 0.0% (0 signals) | **Medium/High** | **Very High** (resolves 'Unknown' data loss) | **CRITICAL** (High ROI) |
| **2** | **Event Table Unification** | **Low** | **Low** | 0.0% (already unified) | **Low** (already unified) | **Medium** (protects against sync failures) | **HIGH** (Medium ROI) |
| **3** | **Financial Results Integration** | **Low** | **Low** | N/A (already unified) | N/A (already unified) | N/A | **N/A** (Complete) |
| **4** | **Board Meeting Integration** | **Low** | **Low** | N/A (already unified) | N/A (already unified) | N/A | **N/A** (Complete) |
| **5** | **Theme Allocation** | **High** | **High** | **Very High** (50+ signals) | **Very High** | **Low** (introduces massive data noise) | **HOLD** (Low ROI due to risk) |

---

## 2. Detailed Findings & Strategic Priorities

### Priority 1: Unknown Symbol Recovery (HIGH ROI)
*   **Why:** Resolving the company symbols for the 4 M&A events from `'Unknown'` to their active tickers (`532380.BO`, `513343.BO`, `514414.BO`, `RBA.NS`) is extremely low effort. While it yields 0 historical signals due to lack of news mentions, it is crucial for future live trading and prevents data loss.
*   **Action:** Append the 4 companies to `company_master.csv` and run the `update_unknown_symbols.py` database migration script.

### Priority 2: Event Table Unification (MEDIUM ROI)
*   **Why:** The specialized tables are already duplicated into `corporate_events` by the crawler. However, querying all three tables in the signal engine with a `UNION` query adds a layer of safety against database sync drift.
*   **Action:** Update the SQL query in `signal_engine.py`.

### Priority 5: Theme Allocation (LOW ROI DUE TO HIGH RISK)
*   **Why:** Although it offers a massive increase in signal volume (50+ signals), the risk of false positives is extremely high because theme velocity spikes lack stock-specific catalysts or sentiment direction filters.
*   **Action:** Put on hold until sentiment direction filters and constituents weighting models are implemented.
