# Decisions Log: MARKET_INTEL

This document tracks key architectural, technical, and strategic decisions made during the evolution of the MARKET_INTEL platform.

---

## Decision 1: Freeze Theme Expansion
*   **Date:** June 8, 2026
*   **Status:** Approved
*   **Reason:** The system previously faced an "infinite expansion loop" where the AI model continuously attempted to classify articles into new, highly specific theme categories. This led to fragmented theme data, low statistical relevance for velocities, and excessive token usage.
*   **Impact:** A frozen list of 16 core structural themes was established:
    *   `AI`, `Semiconductor`, `Banking`, `Capital Markets`, `Energy`, `Defence`, `Pharma`, `Digital Infrastructure`, `Green Energy`, `Telecom`, `Space Economy`, `Macro Economy`, `Commodities`, `Metals & Mining`, `EV`, `Technology`.
    *   Ingestion and classification scripts (`enrich_news.py`, `save_keywords.py`) are strictly locked to these themes. Unclassified or outlying themes are logged for manual dictionary review in `AUDIT/` rather than auto-expanding the database schema.

---

## Decision 2: Use Next-Day Open Price for Entry Price
*   **Date:** June 9, 2026
*   **Status:** Approved
*   **Reason:** In quantitative backtesting, using the closing price of the signal trigger date introduces look-ahead bias, as news or notices published after market hours cannot be traded at that day's close. 
*   **Impact:** 
    *   The entry price ($P_{\text{entry}}$) is strictly defined as the **Open price of the next available trading day** following the signal trigger date.
    *   Return calculations for 5-day and 10-day holds are computed as:
        $$\text{Return}_{5d} = \frac{P_{5d\text{ Close}} - P_{\text{entry Open}}}{P_{\text{entry Open}}} \times 100$$
    *   This ensures realistic trade execution replication.

---

## Decision 3: Decouple Databases into Specialized Files
*   **Date:** June 7, 2026
*   **Status:** Approved
*   **Reason:** Storing news text, high-frequency price history, corporate events, and social media tweets in a single SQLite database leads to frequent file locking and database congestion, especially when n8n pipelines are executing writes concurrently with dashboard reads.
*   **Impact:** The database tier was split into four isolated, single-purpose SQLite database files:
    1.  `market_intel.db`: Main database for text analysis, mention aggregates, theme velocities, and convergence signals.
    2.  `price_data.db`: High-volume master price history (OHLCV + Adj Close) for backtesting.
    3.  `corporate_events.db`: Exchange filings, board meeting schedules, and financial results.
    4.  `twitter_intel.db`: Social media sentiment and raw tweet captures.
    *   Scripts leverage simple SQLite connectors targeting specific databases, avoiding complex multi-database locks.

---

## Decision 4: Use Adjusted Close Prices for Backtesting returns
*   **Date:** June 10, 2026
*   **Status:** Approved
*   **Reason:** Stock splits, bonus issues, and dividends cause artificial price drops that distort simple return calculations. Using standard Close prices would register false losses for corporate events that occur around corporate actions.
*   **Impact:** 
    *   Altered `price_history` schema in `price_data.db` to store `adj_close` alongside standard prices.
    *   Configured `validate_signals.py` to extract and calculate returns using `adj_close` for forward price points.
    *   `price_loader.py` fetches the splitting/dividend-adjusted close from `yfinance`.

---

## Decision 5: Rule-Based Fallback for yfinance MultiIndex DataFrame
*   **Date:** June 10, 2026
*   **Status:** Approved
*   **Reason:** In newer versions of `yfinance`, downloading multiple tickers simultaneously returns a MultiIndex DataFrame where the `'Adj Close'` column is omitted if auto-adjust is enabled. This previously crashed the loader with a `KeyError`.
*   **Impact:** 
    *   Implemented a dynamic row parser check in `price_loader.py` that verifies index columns on connection.
    *   Falls back to standard `'Close'` values if `'Adj Close'` is absent:
        `adj_close = float(row['Adj Close']) if 'Adj Close' in row.index else float(row['Close'])`
    *   Ensures uninterrupted daily incremental cron downloads.
