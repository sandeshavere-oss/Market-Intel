# Event Table Unification Report: MARKET_INTEL

**Prepared by:** Lead Database Architect  
**Date:** June 10, 2026  
**Status:** Completed  

This report analyzes the relationships, overlap, and coverage gaps between the unified `corporate_events` table and the specialized `board_meetings` and `financial_results` tables in `corporate_events.db`.

---

## 1. Event Table Auditing & Metrics

We verified the live records across all three tables in `corporate_events.db`:

*   **Total Events in `corporate_events`:** 6 rows
*   **Total Events in `board_meetings`:** 1 row
*   **Total Events in `financial_results`:** 1 row

### Overlap Analysis
Our audit confirms a **100% overlap** of the specialized tables into the unified table.
*   **`board_meetings` row:** `RELIANCE` on `June 15, 2026` is duplicated as Event ID 5 in `corporate_events` (Type: `board_meeting`).
*   **`financial_results` row:** `TCS` on `2026-06-07` is duplicated as Event ID 6 in `corporate_events` (Type: `financial_results`).
*   **Other 4 events in `corporate_events`:** M&A notices (takeovers) which do not map to board meetings or financial result tables.

### Missing Events Not Visible to the Signal Engine
*   **Count:** 0
*   *Explanation:* The signal engine queries the unified `corporate_events` table. Since all scheduled events from `board_meetings` and `financial_results` are already successfully copied to `corporate_events` by the ingestion pipeline, no events were hidden from the signal engine.

---

## 2. Unification Impact Estimation

If the signal engine is updated to query all three tables using a unified SQL query:

*   **Additional Companies Eligible:** **0** (no new company symbols are introduced).
*   **Additional Signals Generated:** **0** (the signal engine already generated signals for the Reliance and TCS events because it was querying the unified table).

---

## 3. Technical Recommendations (ROI Assessment)

*   **ROI Rating:** **Medium/Low**
*   **Reasoning:** While there is no immediate signal increase (since the ingestion pipeline already unifies the events), updating the signal engine to query all three tables directly using a SQL `UNION` makes the pipeline robust against potential sync failures or custom entries made directly to the specialized tables.
*   **Action Plan:**
    *   Update [signal_engine.py](file:///d:/MARKET_INTEL/NEWS_ENGINE/signal_engine.py) to fetch events from `corporate_events`, `board_meetings`, and `financial_results` using a unified query and deduplicate them in Python using a unique key `(company_symbol, event_date, event_type)`.
