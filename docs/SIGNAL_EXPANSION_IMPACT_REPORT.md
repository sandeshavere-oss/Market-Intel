# Signal Expansion Impact Study: MARKET_INTEL

**Prepared by:** Lead Signal Researcher & Analyst  
**Date:** June 10, 2026  
**Status:** Completed  

This report simulates and evaluates the quantitative impact on signal counts and universe coverage under various expansion scenarios, and ranks the optimization opportunities.

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

For the one company that did have historical mentions (**Restaurant Brands Asia** / `RBA.NS` with 3 mentions), the daily count on each matching day was exactly 1. Because the signal engine enforces a noise filter threshold of `today_count >= 2`, these mentions did not trigger a velocity spike and therefore did not generate a convergence signal.

### Why does unifying the tables result in 0% signal increase?
The crawler script (`save_corp_data.py`) automatically duplicates and consolidates all records from the specialized tables (`board_meetings` and `financial_results`) into the unified `corporate_events` table. Since the signal engine already queries the unified table, it already saw all available events.

---

## 3. Opportunity Rankings & ROI Analysis

Below we evaluate and rank the signal coverage expansion opportunities by signal increase, data quality, implementation effort, and ROI:

| Rank | Opportunity | Signal Increase (Hist/Live) | Data Quality | Implementation Effort | ROI | Status / Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Unknown Symbol Recovery** | 0.0% / **Medium-High** | **Very High** (prevents M&A data loss) | **Low** (one-off script + master csv update) | **Very High** | **IMPLEMENTED** |
| **2** | **Event Table Unification** | 0.0% / **Low** | **Medium** (protects against sync failures) | **Low** (update SQL query in signal engine) | **High** | **IMPLEMENTED** |
| **3** | **Secondary Unconverged Velocity Signals** | **High** (~20+ signals) | **Medium** (requires technical breakouts to validate) | **Medium** (add breakout indicators to engine) | **Medium** | **PLANNED** |
| **4** | **Constituent Theme Allocation** | **Very High** (~50+ signals) | **Low** (introduces massive data noise/chatter) | **High** (requires constituents weight models) | **Low** | **HOLD** |

### Detailed Evaluation

> [!NOTE]
> **Priority 1: Unknown Symbol Recovery**
> Resolving the company symbols for the 4 M&A events from `'Unknown'` to their active tickers (`532380.BO`, `513343.BO`, `514414.BO`, `RBA.NS`) is extremely low effort. While it yields 0 historical signals due to lack of news mentions, it is crucial for future live trading and prevents data loss.

> [!IMPORTANT]
> **Priority 2: Event Table Unification**
> The specialized tables are already duplicated into `corporate_events` by the crawler. However, querying all three tables in the signal engine with a `UNION` query adds a layer of safety against database sync drift.

> [!WARNING]
> **Priority 3: Secondary Unconverged Signals**
> Allowing high-conviction velocity spikes (e.g. velocity > 10.0x) to generate secondary signals, using technical filters (such as volume breakout) as validation instead of corporate event schedules. This is a valuable extension, but requires additional validation to filter noise.

> [!CAUTION]
> **Priority 4: Constituent Theme Allocation (HOLD)**
> Although it offers a massive increase in signal volume (50+ signals), the risk of false positives is extremely high because theme velocity spikes lack stock-specific catalysts or sentiment direction filters. Put on hold until sentiment filters are implemented.

---

## 4. Final Recommendations
- **Maintain Current Thresholds:** Do not lower the mention volume threshold below 2 or the velocity threshold below 2.5, as this would generate noisy and false signals.
- **Deploy to Live Systems:** Run Scenario D (Full Unification) and Scenario B (Unknown Symbols Resolved) to ensure future live runs capture these signals as new news articles are ingested.
