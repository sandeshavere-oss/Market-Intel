# Unknown Symbol Recovery Report: MARKET_INTEL

**Prepared by:** Lead Database Architect & Quantitative Analyst  
**Date:** June 10, 2026  
**Status:** Completed  

This report documents the audit and recovery analysis of corporate events in `corporate_events.db` where the `company_symbol` column was resolved as `'Unknown'`.

---

## 1. Executive Summary

During our signal coverage audit, we discovered that **4 out of 6 corporate events** (66.7%) in the database were marked with `company_symbol = 'Unknown'`. Because the signal engine ignores events without resolved tickers, this constituted a major coverage bottleneck.

Through PDF text extraction on the attachment links (`guid` column), we successfully identified the target company names for **100%** of these events and resolved their active Yahoo Finance ticker symbols.

---

## 2. Unknown Symbol Registry & Recovery Findings

All 4 affected events are **M&A Takeover Notices** filed on June 8, 2026.

| Event ID | Title / LLM Purpose | Link (PDF GUID) | Extracted Company Name | Resolved Ticker Symbol | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Offer to Buy – Acquisition Window | [20260608-24.pdf](https://www.bseindia.com/downloads/UploadDocs/Notices/20260608-24/20260608-24.pdf) | BABA ARTS LTD | `532380.BO` (BSE) | **RECOVERED** |
| **2** | Offer to Buy – Acquisition Window | [20260608-23.pdf](https://www.bseindia.com/downloads/UploadDocs/Notices/20260608-23/20260608-23.pdf) | GRAND FOUNDRY Ltd | `513343.BO` (BSE) | **RECOVERED** |
| **3** | Acquisition Window (Takeover) | [20260608-10.pdf](https://www.bseindia.com/downloads/UploadDocs/Notices/20260608-10/20260608-10.pdf) | OXFORD INDUSTRIES LIMITED | `514414.BO` (BSE) | **RECOVERED** |
| **4** | Offer to Buy – Acquisition Window | [20260608-2.pdf](https://www.bseindia.com/downloads/UploadDocs/Notices/20260608-2/20260608-2.pdf) | RESTAURANT BRANDS ASIA LTD | `RBA.NS` (NSE) | **RECOVERED** |

---

## 3. Recovery Feasibility & Metrics

*   **Current Unknown Count:** 4
*   **Recoverable Count:** 4 (100.0%)
*   **Unrecoverable Count:** 0
*   **Expected Additional Signals (Historical):** 0  
    *   *Explanation:* Because these 4 companies were missing from `company_master.csv` during the historical news ingestion period (May 31, 2026 to June 9, 2026), they have **zero mentions** recorded in the `keywords` or `company_mentions` tables. Since their mention velocity remains 0, they cannot trigger a historical convergence signal even after symbol recovery.
*   **Expected Additional Signals (Future / Live):** **Medium/High**  
    *   *Explanation:* Appending these companies to `company_master.csv` enables the news poller to match future articles and calculate velocities, preventing future signal loss.

---

## 4. Technical Recommendations (ROI Assessment)

*   **ROI Rating:** **High**
*   **Reasoning:** Although the historical signal yield is 0, resolving this issue is critical for live operational parity and prevents future data loss. The effort required is extremely low.
*   **Action Plan:**
    1.  Append all 4 companies, symbols, and aliases to `company_master.csv`.
    2.  Execute a one-off database update script (`update_unknown_symbols.py`) to map the 4 records in `corporate_events.db` using their GUID links.
