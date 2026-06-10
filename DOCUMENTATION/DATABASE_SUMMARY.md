# Database Summary: MARKET_INTEL

This document summarizes the database storage layer of the `MARKET_INTEL` platform. To prevent write-concurrency locks during high-frequency data ingestion, the database tier is split into four specialized SQLite database files located under `D:/MARKET_INTEL/DATABASE/`.

---

## 1. Databases & Live Record Counts

| Database Name | Table Name | Purpose | Record Count (June 10, 2026) |
| :--- | :--- | :--- | :--- |
| **`market_intel.db`** | `keywords` | Raw ingested articles, tagged keywords, and AI metadata. | 1,392 rows |
| | `processed_articles` | Unique URL registry to avoid duplicate news processing. | 1,373 rows |
| | `company_mentions` | Daily counts of stock ticker mentions. | 460 rows |
| | `theme_velocity` | Rolling theme averages and momentum Z-Scores. | 176 rows |
| | `event_signals` | Generated convergence signals (velocity spike + board meeting). | 3 rows |
| | `signal_performance` | Calculates entry Open, exit Close, 5d/10d returns, and outcomes. | 2 rows |
| | `daily_intelligence` | Markdown-formatted daily briefing newsletters. | 3 rows |
| | `corporate_events` | Ingested corporate notifications (internal staging). | 2 rows |
| | `workflow_state` | Ingestion script cursors. | 0 rows |
| **`price_data.db`** | `price_history` | OHLCV prices including splitting/dividend-adjusted close. | 39,720 rows |
| | `daily_prices` | Legacy price tracking. | 31,793 rows |
| **`corporate_events.db`**| `corporate_events` | General exchange filings and disclosures. | 6 rows |
| | `board_meetings` | Scheduled board meeting dates and purposes. | 1 row |
| | `financial_results` | Corporate quarterly and annual earnings data. | 1 row |
| **`twitter_intel.db`** | `tweets` | Scraped quant handle tweets and sentiment scores. | 150 rows |

---

## 2. Key Schemas & Relationships

### `keywords` Table (`market_intel.db`)
*   **Ingestion Timestamps:** Includes `source_timestamp` (publication date/time) and `system_timestamp` (actual write time) to calculate crawler latency.
*   **Enrichment fields:** `sentiment` (Positive, Negative, Neutral), `impact_score` (1-5), and resolved `related_companies` (e.g. TCS, RELIANCE).

### `price_history` Table (`price_data.db`)
*   **Adjusted Close:** Features an `adj_close` column to ensure that return calculations are not distorted by stock splits, bonus shares, or dividends.

### `signal_performance` Table (`market_intel.db`)
*   **Foreign Key Constraint:** Linked directly to `event_signals(id)` via `signal_id`.
*   **Trading open entry:** entry price is taken from next-day Open to replicate real-world trade entry, preventing look-ahead bias. Outcomes are categorized as `WIN` (positive return), `LOSS` (negative return), `NEUTRAL`, or `PENDING` (if 10 days of prices are not yet available).
