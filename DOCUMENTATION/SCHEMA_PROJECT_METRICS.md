# SQL Schema Documentation: Project Metrics Database

## Database Overview
- **Database File:** `project_metrics.db`
- **Path Location:** `DATABASE/project_metrics.db`
- **Purpose:** Centralized storage for system-wide auditing metrics, tracking data ingestion, entity matches, signal generation, outcomes, error frequencies, and database growth over time.
- **Engine:** SQLite 3

---

## Tables

### 1. `daily_metrics`
This table stores a single row of aggregated statistics for each audited date.

#### Table Definition
```sql
CREATE TABLE IF NOT EXISTS daily_metrics (
    date TEXT PRIMARY KEY,
    news_articles INTEGER,
    tweets INTEGER,
    bse_events INTEGER,
    company_matches INTEGER,
    theme_matches INTEGER,
    signal_candidates INTEGER,
    validated_signals INTEGER,
    wins INTEGER,
    losses INTEGER,
    workflow_errors INTEGER,
    database_size_mb REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Fields Description

| Column Name | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `date` | TEXT | PRIMARY KEY | The target date for which the system metrics are collected (Format: `YYYY-MM-DD`). |
| `news_articles` | INTEGER | | Count of RSS news articles processed on this date (extracted from `market_intel.db -> processed_articles`). |
| `tweets` | INTEGER | | Count of tweets captured on this date (extracted from `twitter_intel.db -> tweets`). |
| `bse_events` | INTEGER | | Count of BSE corporate events ingested on this date (extracted from `market_intel.db -> corporate_events`). |
| `company_matches` | INTEGER | | Sum of company matches identified in processed text on this date (extracted from `market_intel.db -> keywords` or `company_mentions`). |
| `theme_matches` | INTEGER | | Sum of theme matches identified in processed text on this date (extracted from `market_intel.db -> keywords` or `theme_velocity`). |
| `signal_candidates` | INTEGER | | Count of trading signal candidates generated on this date (extracted from `market_intel.db -> event_signals`). |
| `validated_signals` | INTEGER | | Count of signals that underwent outcome validation on this date (extracted from `market_intel.db -> signal_performance`). |
| `wins` | INTEGER | | Count of validated signals resulting in a positive return (outcome = `'WIN'`) on this date. |
| `losses` | INTEGER | | Count of validated signals resulting in a negative return (outcome = `'LOSS'`) on this date. |
| `workflow_errors` | INTEGER | | Total count of `ERROR`, `FATAL`, `EXCEPTION`, or `CRITICAL` log messages matched in the logs directory on this date. |
| `database_size_mb` | REAL | | Combined size of all SQLite databases (`*.db`) in the `DATABASE` folder at audit execution time (in Megabytes). |
| `created_at` | DATETIME | DEFAULT `CURRENT_TIMESTAMP` | The timestamp when the record was inserted or updated. |

---

## Ingestions and Calculations Mapping

- **News Articles Count:**
  `SELECT COUNT(*) FROM processed_articles WHERE date(processed_at) = :date`
- **Tweets Count:**
  `SELECT COUNT(*) FROM tweets WHERE date(created_at) = :date`
- **BSE Corporate Events Count:**
  `SELECT COUNT(*) FROM corporate_events WHERE date(ingested_at) = :date`
- **Company Matches Count:**
  `SELECT SUM(company_match_count) FROM keywords WHERE date(created_at) = :date` (falling back to `SUM(mentions) FROM company_mentions WHERE date = :date` if zero).
- **Theme Matches Count:**
  `SELECT SUM(theme_match_count) FROM keywords WHERE date(created_at) = :date` (falling back to `SUM(mentions_today) FROM theme_velocity WHERE date = :date` if zero).
- **Signal Candidates Count:**
  `SELECT COUNT(*) FROM event_signals WHERE date(created_at) = :date` (falling back to querying by `signal_date = :date` if zero).
- **Validated Signals Count:**
  `SELECT COUNT(*) FROM signal_performance WHERE outcome != 'PENDING' AND date(updated_at) = :date` (falling back to querying by `signal_date = :date` if zero).
- **Wins Count:**
  `SELECT COUNT(*) FROM signal_performance WHERE outcome = 'WIN' AND date(updated_at) = :date` (falling back to querying by `signal_date = :date` if zero).
- **Losses Count:**
  `SELECT COUNT(*) FROM signal_performance WHERE outcome = 'LOSS' AND date(updated_at) = :date` (falling back to querying by `signal_date = :date` if zero).
