# MARKET_INTEL: Database Schema Reference Guide
**Version:** 2.2.0  
**Last Updated:** June 10, 2026

This document specifies the table structures, keys, constraints, and relationships across all SQLite databases utilized by the `MARKET_INTEL` platform, including live record counts as of the latest audit.

---

## 1. Main Database: `market_intel.db`
**Purpose:** Houses text ingestion, entity mentions, theme momentum statistics, convergence signals, and backtest results.
**Live Record Count:** ~3,400 total active rows across tables.

### Table: `keywords`
*   **Purpose:** Stores raw news articles, scraped exchange filings, tagged keywords, and classification metadata.
*   **Columns:**
    *   `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT)
    *   `title` (TEXT)
    *   `raw_text` (TEXT, NOT NULL)
    *   `keywords` (TEXT, NOT NULL)
    *   `source` (TEXT)
    *   `created_at` (TEXT, NOT NULL)
    *   `related_companies` (TEXT)
    *   `theme` (TEXT)
    *   `link` (TEXT)
    *   `processed` (INTEGER, DEFAULT 0)
    *   `company_match_count` (INTEGER, DEFAULT 0)
    *   `theme_match_count` (INTEGER, DEFAULT 0)
    *   `sentiment` (TEXT)
    *   `impact_score` (TEXT)
    *   `enriched_at` (TEXT)
    *   `source_timestamp` (TEXT) - Original publication date/time.
    *   `system_timestamp` (TEXT) - Ingestion insertion timestamp.
*   **Record Count:** 1,392 rows

### Table: `processed_articles`
*   **Purpose:** Tracks unique URLs/IDs to prevent duplicate news processing.
*   **Columns:**
    *   `article_id` (TEXT, PRIMARY KEY) - Typically the article URL or BSE Notice GUID.
    *   `title` (TEXT)
    *   `source_feed` (TEXT)
    *   `processed_at` (TEXT)
*   **Record Count:** 1,373 rows

### Table: `workflow_state`
*   **Purpose:** Manages cursor offsets for Python ingestion scripts.
*   **Columns:**
    *   `workflow_name` (TEXT, PRIMARY KEY)
    *   `last_processed_id` (INTEGER)
*   **Record Count:** 0 rows (active cursors are stored in memory or default to first-run).

### Table: `daily_intelligence`
*   **Purpose:** Renders AI-generated briefing newsletter briefs.
*   **Columns:**
    *   `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT)
    *   `summary_date` (TEXT) - Format `YYYY-MM-DD`.
    *   `top_themes` (TEXT) - Markdown listing top themes.
    *   `top_companies` (TEXT) - Markdown listing top companies.
    *   `important_events` (TEXT) - Markdown summary of core corporate events.
    *   `raw_summary` (TEXT) - Markdown full text.
    *   `created_at` (TEXT)
*   **Record Count:** 3 rows

### Table: `corporate_events` (Internal Ingestion)
*   **Purpose:** Ingested raw corporate disclosures from news feeds.
*   **Columns:**
    *   `id` (INTEGER, PRIMARY KEY)
    *   `article_id` (TEXT)
    *   `title` (TEXT)
    *   `company_name` (TEXT)
    *   `bse_code` (TEXT, DEFAULT '')
    *   `event_type` (TEXT)
    *   `event_category` (TEXT)
    *   `sentiment` (TEXT)
    *   `impact_score` (INTEGER, DEFAULT 0)
    *   `link` (TEXT)
    *   `source_feed` (TEXT, DEFAULT 'BSE')
    *   `published_at` (TEXT)
    *   `raw_ollama_response` (TEXT)
    *   `ingested_at` (TEXT, DEFAULT datetime('now'))
*   **Record Count:** 2 rows

### Table: `company_mentions`
*   **Purpose:** Aggregates daily entity counts per stock ticker symbol.
*   **Columns:**
    *   `company` (TEXT, PRIMARY KEY) - Stock ticker (e.g. TCS).
    *   `date` (TEXT, PRIMARY KEY) - Format `YYYY-MM-DD`.
    *   `mentions` (INTEGER)
*   **Record Count:** 489 rows

### Table: `theme_velocity`
*   **Purpose:** Computes rolling averages and Z-scores for standard themes.
*   **Columns:**
    *   `theme` (TEXT, PRIMARY KEY) - Frozen theme term.
    *   `date` (TEXT, PRIMARY KEY) - Format `YYYY-MM-DD`.
    *   `mentions_today` (INTEGER)
    *   `7d_avg` (REAL)
    *   `30d_avg` (REAL)
    *   `z_score` (REAL)
*   **Record Count:** 176 rows

### Table: `event_signals`
*   **Purpose:** Triggers convergence signals (velocity > 2.5x + board meeting in 7 days).
*   **Columns:**
    *   `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT)
    *   `company` (TEXT) - Stock ticker symbol.
    *   `signal_date` (TEXT) - Format `YYYY-MM-DD`.
    *   `velocity` (REAL)
    *   `today_mentions` (INTEGER)
    *   `avg_mentions` (REAL)
    *   `event_id` (INTEGER)
    *   `event_type` (TEXT)
    *   `event_date` (TEXT)
    *   `event_description` (TEXT)
    *   `signal_strength` (TEXT) - Conviction level (`HIGH`, `MEDIUM`).
    *   `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)
*   **Record Count:** 3 rows

### Table: `signal_performance`
*   **Purpose:** Performs price checks and forward hold return evaluations.
*   **Columns:**
    *   `signal_id` (INTEGER, PRIMARY KEY) - Matches `event_signals(id)`.
    *   `company` (TEXT)
    *   `signal_date` (TEXT)
    *   `price_at_signal` (REAL) - Next-day Open price.
    *   `price_5d_later` (REAL) - 5-day close.
    *   `price_10d_later` (REAL) - 10-day close.
    *   `return_5d` (REAL) - Percentage return after 5 trading days.
    *   `return_10d` (REAL) - Percentage return after 10 trading days.
    *   `outcome` (TEXT) - Status (`WIN`, `LOSS`, `NEUTRAL`, `PENDING`).
    *   `updated_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)
*   **Constraints:**
    *   *Foreign Key:* `signal_id` references `event_signals(id)` ON DELETE CASCADE.
*   **Record Count:** 2 rows

---

## 2. Price History Database: `price_data.db`
**Purpose:** Stores daily OHLCV and adjusted prices for constituents.
**Live Record Count:** ~71,500 total active rows.

### Table: `price_history`
*   **Purpose:** Master OHLCV price histories.
*   **Columns:**
    *   `symbol` (TEXT, PRIMARY KEY)
    *   `date` (TEXT, PRIMARY KEY) - Format `YYYY-MM-DD`.
    *   `open` (REAL)
    *   `high` (REAL)
    *   `low` (REAL)
    *   `close` (REAL)
    *   `adj_close` (REAL) - Splitting & dividend-adjusted closing price.
    *   `volume` (INTEGER)
    *   `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)
*   **Record Count:** 39,720 rows

### Table: `daily_prices`
*   **Purpose:** Legacy price tracking table.
*   **Columns:**
    *   `symbol` (TEXT, PRIMARY KEY)
    *   `date` (TEXT, PRIMARY KEY) - Format `YYYY-MM-DD`.
    *   `open` (REAL)
    *   `high` (REAL)
    *   `low` (REAL)
    *   `close` (REAL)
    *   `volume` (INTEGER)
*   **Record Count:** 31,793 rows

---

## 3. Corporate Filings Database: `corporate_events.db`
**Purpose:** Logs official regulatory notifications filed by corporates.
**Live Record Count:** 8 total active rows.

### Table: `board_meetings`
*   **Purpose:** Schedules of upcoming corporate board meetings.
*   **Columns:**
    *   `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT)
    *   `company_symbol` (TEXT)
    *   `meeting_date` (TEXT) - Format `YYYY-MM-DD`.
    *   `purpose` (TEXT) - Intended board discussion purpose.
    *   `source` (TEXT) - Exchange source.
    *   `guid` (TEXT) - Unique notification identifier.
    *   `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)
*   **Record Count:** 1 row

### Table: `financial_results`
*   **Purpose:** Disclosed quarterly and annual financial metrics.
*   **Columns:**
    *   `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT)
    *   `company_symbol` (TEXT)
    *   `quarter` (TEXT)
    *   `financial_year` (TEXT)
    *   `revenue` (REAL) - In Crores.
    *   `net_profit` (REAL) - In Crores.
    *   `outcome_summary` (TEXT)
    *   `guid` (TEXT)
    *   `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)
*   **Record Count:** 1 row

### Table: `corporate_events` (Official Records)
*   **Purpose:** General disclosures filed to exchange boards.
*   **Columns:**
    *   `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT)
    *   `company_symbol` (TEXT)
    *   `event_date` (TEXT)
    *   `event_type` (TEXT)
    *   `description` (TEXT)
    *   `source` (TEXT)
    *   `guid` (TEXT)
    *   `created_at` (DATETIME, DEFAULT CURRENT_TIMESTAMP)
*   **Record Count:** 6 rows

---

## 4. Twitter Ingestion Database: `twitter_intel.db`
**Purpose:** Stores crawled tweets, sentiment tags, and impact scores.
**Live Record Count:** 150 total active rows.

### Table: `tweets`
*   **Purpose:** Crawled social media posts.
*   **Columns:**
    *   `id` (INTEGER, PRIMARY KEY, AUTOINCREMENT)
    *   `twitter_handle` (TEXT)
    *   `tweet_text` (TEXT)
    *   `tweet_url` (TEXT)
    *   `sentiment` (TEXT)
    *   `impact` (TEXT)
    *   `created_at` (TEXT)
*   **Record Count:** 150 rows
