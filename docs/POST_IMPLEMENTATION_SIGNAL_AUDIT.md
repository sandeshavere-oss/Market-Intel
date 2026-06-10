# Post-Implementation Signal Audit: MARKET_INTEL

**Prepared by:** Lead Quantitative Engineer & Project Director  
**Date:** June 10, 2026  
**Status:** Completed  

This report documents the post-implementation audit of the convergence signal engine following the recovery of unknown company symbols and the unification of event source tables.

---

## 1. Summary of Changes Implemented

1.  **Unknown Symbol Recovery:** 
    *   Mapped and recovered **4 out of 4 (100.0%)** takeover events that were previously flagged with `company_symbol = 'Unknown'`.
    *   Assigned correct Yahoo Finance ticker symbols (`532380.BO`, `513343.BO`, `514414.BO`, `RBA.NS`) in the database.
    *   Appended all 4 recovered companies to `MAPPINGS/company_master.csv` with their aliases to allow mention tracking in future live runs.

2.  **Event Table Unification:**
    *   Updated the signal engine query in `NEWS_ENGINE/signal_engine.py` to pull events concurrently from `corporate_events`, `board_meetings`, and `financial_results` using a SQL `UNION` query.
    *   Implemented Python-based deduplication using `(company_symbol, event_date_standardized, event_type)` keys to ensure no duplicate signals are generated from overlapping tables.

---

## 2. Signal Funnel Comparison (Before vs. After)

The table below shows the impact of these changes on historical signal generation (May 31, 2026 to June 9, 2026).

| Metric | Before Implementation | After Implementation | Change | Explanation |
| :--- | :--- | :--- | :--- | :--- |
| **Total Ingested Articles** | 1,393 | 1,393 | 0 (0.0%) | No new articles were ingested. |
| **Company Matches** | 458 | 460 | +2 (+0.4%) | Added RBA.NS which has 3 historical mentions. |
| **Matched Events** | 2 | 6 | +4 (+200.0%) | Mapped the 4 takeover events from 'Unknown' to resolved tickers. |
| **Signals Generated** | 3 | 3 | 0 (0.0%) | No new historical signals generated. |
| **Coverage Increase %** | 0.0% | **0.0% (Historical)** | 0.0% | See section below for details. |

### Why Historical Signal Count Remained at 3
Although we recovered 4 M&A events:
1.  **BABA ARTS LTD** (`532380.BO`), **GRAND FOUNDRY Ltd** (`513343.BO`), and **OXFORD INDUSTRIES LIMITED** (`514414.BO`) are micro-cap companies with **zero mentions** in our news database (`keywords` table) during the historical period. Since their mention velocity remains 0, they could not trigger a signal.
2.  **RESTAURANT BRANDS ASIA LTD** (`RBA.NS`) was matched in the news database with **3 mentions** across June 2nd, June 3rd, and June 6th. However, since the daily count was 1 on each day, it did not satisfy the signal engine's noise threshold (`today_count >= 2`) or velocity spike threshold (`velocity > 2.5`).
3.  Therefore, while event coverage expanded by **200%**, historical signal volume remained stable at **3**. However, this protects the live cron runs from future signal loss as news velocity calculates dynamically.

---

## 3. Signal Performance & Statistics

Following the historical re-run and validation, the signal performance records remain stable:

*   **Total Signals:** 3
*   **Completed Signals:** 1 (`TCS` on 2026-06-01)
*   **Pending Signals:** 2 (`TCS` on 2026-06-03, `RELIANCE` on 2026-06-09)
*   **Win Count:** 0
*   **Loss Count:** 1
*   **Neutral Count:** 0
*   **Win Rate %:** 0.0%
*   **Average Return (5D):** -7.38% (LOSS)

---

## 4. Operational Impact & Risks Remaining

*   **System Integrity:** Successfully resolved the `'Unknown'` data loss bottleneck.
*   **Redundancy:** The unified SQL query query prevents database synchronization drift between crawlers.
*   **Remaining Risks:** Signal generation remains sensitive to a lack of sentiment directionality. Spikes in mentions driven by negative sentiment can still trigger false-positive buy signals. Adding a sentiment filter remains the highest priority recommendation.
