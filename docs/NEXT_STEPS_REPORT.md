# Recommended Next Steps Report: MARKET_INTEL

This report outlines the technical changes, priority tasks, and long-term milestones recommended to enhance the `MARKET_INTEL` platform.

---

## 1. Immediate Priority (Current Sprint)

### Task A: Benchmark Relative Return Normalization
*   **Problem:** Currently, the system calculates absolute returns for stock signals. During general bull markets, absolute returns may look positive even if the stock underperforms the benchmark index. This makes it difficult to prove if our signal engine generates true **Alpha ($\alpha$)**.
*   **Solution:** 
    1.  Add a `nifty50_history` table in `price_data.db` to log daily Nifty 50 index prices.
    2.  Update `price_loader.py` to incrementally download Nifty 50 prices (ticker `^NSEI`).
    3.  Modify `validate_signals.py` to calculate the Nifty 50 return over the matching 5-day and 10-day holding periods for each signal.
    4.  Update the `signal_performance` schema and calculate:
        $$\text{Alpha}_{5d} = \text{Return}_{5d} - \text{Nifty50 Return}_{5d}$$
        $$\text{Alpha}_{10d} = \text{Return}_{10d} - \text{Nifty50 Return}_{10d}$$
    5.  Display normalized relative returns and Alpha metrics on the Streamlit dashboard.

---

## 2. Infrastructure Priority

### Task B: Asynchronous LLM Job Queue
*   **Problem:** Local LLM queries (via Ollama Mistral:7b) are computationally expensive and run synchronously within the n8n ingestion crons. This creates a processing bottleneck; if multiple RSS feeds trigger simultaneously, the script can time out, leading to data loss.
*   **Solution:**
    1.  Create a `job_queue` table in `market_intel.db` to hold raw article texts requiring AI analysis.
    2.  Configure `capture_rss.py` to immediately write incoming articles to the `keywords` table with `processed = 0` and add them to the `job_queue`.
    3.  Create a standalone background script `process_queue.py` that reads jobs from the queue, calls Ollama, updates the `keywords` table with the metadata, and removes the job upon completion.
    4.  Run `process_queue.py` as a continuous daemon or frequent micro-cron.

---

## 3. Secondary Actions & Code Cleanup

### Task C: Cleanup Deprecated Code
*   **Action:** Delete or archive legacy files to eliminate technical confusion.
    *   Delete `NEWS_ENGINE/price_history_loader.py` and `NEWS_ENGINE/price_engine.py` (replaced by `PRICE_ENGINE/price_loader.py`).
    *   Delete `NEWS_ENGINE/signal_engine.py` and `NEWS_ENGINE/performance_tracker.py` (replaced by `SIGNAL_ENGINE/validate_signals.py`).
*   **Mitigation:** Verify all local imports are updated to point to the correct files under `PRICE_ENGINE/` and `SIGNAL_ENGINE/` before removing files.

### Task D: Dynamic File Pathing
*   **Action:** Update hardcoded absolute paths (`D:/MARKET_INTEL/...`) to path-independent code using Python's `pathlib.Path(__file__).resolve().parent`. This ensures that the platform can run seamlessly on other development environments.
