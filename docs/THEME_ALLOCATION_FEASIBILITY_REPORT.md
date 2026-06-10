# Theme-to-Stock Allocation Feasibility Report: MARKET_INTEL

**Prepared by:** Lead Signal Researcher  
**Date:** June 10, 2026  
**Status:** Completed  

This feasibility report analyzes the benefits, risks, and data quality concerns of implementing a "Theme-to-Stock" signal allocation mechanism to map sector-level velocity spikes directly to constituent stock trading signals.

---

## 1. Overview & Context

The `MARKET_INTEL` platform tracks 16 frozen themes. While these themes frequently experience massive velocity spikes (Z-Scores > 2.5), they are ignored by the signal engine, which requires stock-specific mentions and corporate events.

### Top Velocity Sector Themes (May 31 – June 9, 2026)
*   **Banking:** Z-Score: **29.44** (Date: 2026-06-03)
*   **Digital Infrastructure:** Z-Score: **27.98** (Date: 2026-06-03)
*   **Telecom:** Z-Score: **24.83** (Date: 2026-06-03)
*   **Semiconductor:** Z-Score: **16.25** (Date: 2026-06-07)
*   **Green Energy:** Z-Score: **15.56** (Date: 2026-06-03)

---

## 2. Constituent Allocation Analysis

To allocate theme momentum, we mapped themes to top liquid stock tickers from our universe:

*   **Banking constituents:** `HDFCBANK`, `ICICIBANK`, `SBIN`, `KOTAKBANK`, `AXISBANK`
*   **Digital Infrastructure constituents:** `INFY`, `TCS`, `WIPRO`, `TECHM`, `BSOFT`
*   **Telecom constituents:** `BHARTIARTL`, `IDEA`, `INDUSTOWER`
*   **Semiconductor constituents:** `DIXON`, `KAYNES`
*   **Green Energy constituents:** `ADANIGREEN`, `ADANIENSOL`, `RELIANCE`, `NTPC`

### Potential Signal Volume
If a theme Z-Score > 2.5 triggers signals across its top 5 constituent stocks, the system would generate **50+ signals** historically, compared to the current **3 signals** (a >1,500% increase in coverage).

---

## 3. Risks & Feasibility Assessment

### A. High Risk of False Positives (No directional filtering)
*   **Risk:** Sector velocity spikes can be triggered by negative industry news (e.g. regulatory crackdowns on banks or telecom tariff disputes). Triggering long buy entries on all constituents during a negative news spike will lead to severe losses.
*   **Mitigation:** Requires a robust sentiment-directional filter to verify that the theme spike is driven by positive sentiment.

### B. LLM Theme Drift (Data Quality Concern)
*   **Risk:** Theme classifications are determined by the local Ollama LLM. Small changes in prompt parsing can cause articles to drift between themes, leading to noisy velocity calculations.

### C. Lack of Stock-Specific Catalyst
*   **Risk:** A sector-wide theme spike does not guarantee that every constituent will rise. We lose the "corporate event convergence" filter (board meetings/results) which is our strongest shield against noise.

---

## 4. Final Recommendation
*   **Decision:** **DO NOT IMPLEMENT NOW.**
*   **Reasoning:** Although theme allocation offers the highest signal volume increase, it introduces unacceptable risk and data noise. It should only be implemented *after* we have deployed a reliable directional sentiment filter, relative return normalization, and a sector-constituent weighting model.
