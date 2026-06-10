# Signal Expansion Impact Report: MARKET_INTEL

**Prepared by:** Lead Signal Researcher & Analyst  
**Date:** June 10, 2026  
**Status:** Completed  

This report simulates and evaluates the quantitative impact on signal counts and universe coverage under various expansion scenarios.

---

## 1. Simulation Matrix

We modeled signal generation across four scenarios based on the live historical databases (May 31, 2026 to June 9, 2026). 

*   **Scenario A:** Current Engine (queries `corporate_events` table; M&A symbols remain `Unknown`).
*   **Scenario B:** Unknown Symbols Fixed (recovers the 4 M&A symbols).
*   **Scenario C:** Unknown Symbols Fixed + Board Meetings Table Included.
*   **Scenario D:** Unknown Symbols Fixed + Board Meetings + Financial Results Tables Included (full unification).

### Simulation Results Table

| Metrics | Scenario A (Current) | Scenario B (Resolved Symbols) | Scenario C (Resolved + Board Mtgs) | Scenario D (Full Unification) |
| :--- | :--- | :--- | :--- | :--- |
| **Total Signals** | **3** | **3** | **3** | **3** |
| **Unique Companies Covered** | 2 (`TCS`, `RELIANCE`) | 2 (`TCS`, `RELIANCE`) | 2 (`TCS`, `RELIANCE`) | 2 (`TCS`, `RELIANCE`) |
| **Unique Events Covered** | 2 | 2 | 2 | 2 |
| **Signal Increase %** | **0.0%** (base) | **0.0%** | **0.0%** | **0.0%** |

---

## 2. Key Findings & Diagnostic Analysis

### Why does fixing the Unknown symbols result in 0% historical signal increase?
Although we recovered the ticker symbols for the 4 M&A events (`532380.BO`, `513343.BO`, `514414.BO`, `RBA.NS`), these companies are not present in the current `company_master.csv`. As a result, the news poller did not track them, resulting in **0 mentions** in the `keywords` and `company_mentions` tables. 

Since the signal engine requires a mention velocity spike to generate a signal, a company with 0 mentions will never trigger, even if a valid corporate event is registered for it.

### Why does unifying the tables result in 0% signal increase?
The crawler script (`save_corp_data.py`) automatically duplicates and consolidates all records from the specialized tables (`board_meetings` and `financial_results`) into the unified `corporate_events` table. Since the signal engine already queries the unified table, it already saw all available events.

---

## 3. Recommendations
*   **Acknowledge historical limits:** We must recognize that code-level fixes alone will not increase our *historical* signal yield without backfilling the news articles database or expanding our company master dictionary.
*   **Deploy for future parity:** We should still implement Scenario D (Full Unification) and Scenario B (Unknown Symbols Resolved) to ensure future live runs capture these signals as new news articles are ingested.
