# Database Schema Reference: Market-Intel

Market-Intel splits its storage across four separate SQLite database files. This prevents file lock contention during parallel data ingestion (such as active Twitter scraping, RSS polling, and price syncing happening concurrently).

---

## 🏛️ Relational ERD Diagram

The databases are joined logically within the analytics, validation, and presentation layers:

```mermaid
erDiagram
    %% market_intel.db
    KEYWORDS {
        int id PK
        string title
        string raw_text
        string keywords
        string source
        string created_at
        string related_companies
        string theme
        string link
        int processed
        string sentiment
        string impact_score
        string source_timestamp
        string system_timestamp
        string enriched_at
    }

    COMPANY_MENTIONS {
        string company PK
        string date PK
        int mentions
    }

    THEME_VELOCITY {
        string theme PK
        string date PK
        int mentions_today
        float avg_7d
        float avg_30d
        float z_score
    }

    EVENT_SIGNALS {
        int id PK
        string company FK
        string signal_date
        float velocity
        int today_mentions
        float avg_mentions
        int event_id FK
        string event_type
        string event_date
        string event_description
        string signal_strength
        datetime created_at
        float signal_score
    }

    SIGNAL_PERFORMANCE {
        int signal_id PK
        string company FK
        string signal_date
        float price_at_signal
        float price_5d_later
        float price_10d_later
        float return_5d
        float return_10d
        string outcome
        datetime updated_at
    }

    GRAPH_NODES {
        int id PK
        string node_name UK
        string node_type
        string symbol
        datetime created_at
    }

    GRAPH_EDGES {
        int id PK
        int source_node_id FK
        int target_node_id FK
        string relationship_type
        float weight
        datetime created_at
    }

    IMPACT_SIGNALS {
        int id PK
        int article_id
        string event_type
        string expectation_changed
        string first_order_node
        string target_company
        string ticker
        int order_depth
        string direction
        float conviction_score
        float magnitude_score
        string signal_horizon
        float pcr_level
        float iv_percentile
        string signal_date
        int processed
        datetime created_at
    }

    %% price_data.db
    PRICE_HISTORY {
        string symbol PK
        string date PK
        float open
        float high
        float low
        float close
        float adj_close
        int volume
        datetime created_at
    }

    OPTIONS_CHAIN {
        string symbol PK
        string expiry PK
        float strike PK
        string option_type PK
        float ltp
        int oi
        int change_in_oi
        int volume
        float implied_volatility
        float underlying_price
        string snapshot_timestamp PK
        float delta
        float gamma
        float theta
        float vega
        float iv_percentile
        datetime created_at
    }

    OPTIONS_SUMMARY {
        string symbol PK
        string expiry PK
        string snapshot_timestamp PK
        float pcr
        float underlying_price
        int total_call_oi
        int total_put_oi
        int total_call_volume
        int total_put_volume
        datetime created_at
    }

    %% corporate_events.db
    BOARD_MEETINGS {
        int id PK
        string company_symbol
        string meeting_date
        string purpose
        string source
        string guid
        datetime created_at
    }

    %% In-Memory or Logical Joins
    KEYWORDS ||--o{ COMPANY_MENTIONS : "aggregates to"
    KEYWORDS ||--o{ THEME_VELOCITY : "aggregates to"
    COMPANY_MENTIONS ||--o{ EVENT_SIGNALS : "triggers"
    BOARD_MEETINGS ||--o{ EVENT_SIGNALS : "validates"
    EVENT_SIGNALS ||--|| SIGNAL_PERFORMANCE : "evaluates"
    PRICE_HISTORY ||--o{ SIGNAL_PERFORMANCE : "supplies prices"
    GRAPH_NODES ||--o{ GRAPH_EDGES : "defines source/target"
    GRAPH_NODES ||--o{ IMPACT_SIGNALS : "supplies tickers"
    OPTIONS_CHAIN ||--o{ OPTIONS_SUMMARY : "rolls up to"
    OPTIONS_SUMMARY ||--o{ EVENT_SIGNALS : "boosts/penalizes"
```

---

## 🛢️ 1. Main Database: `market_intel.db`

### Table: `keywords`
Stores captured articles, extracted entities, mapped themes, and processing flags.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique record ID |
| `title` | TEXT | | Title of the article/notice |
| `raw_text` | TEXT | | Full extracted content or PDF transcript |
| `keywords` | TEXT | | Comma-separated key phrases |
| `source` | TEXT | | Source (e.g., RSS, Moneycontrol, BSE) |
| `created_at` | TEXT | | Timestamp when ingested |
| `related_companies`| TEXT | | Pipes-separated matched tickers (e.g., `TCS.NS\|INFY.NS`) |
| `theme` | TEXT | | Pipes-separated standardized themes (e.g., `AI\|EV`) |
| `link` | TEXT | UNIQUE | URL/link of the source article |
| `processed` | INTEGER | DEFAULT 0 | 0 = Unprocessed, 1 = Structuring Complete |
| `sentiment` | TEXT | | Sentiment tag (Positive, Negative, Neutral) |
| `impact_score` | TEXT | | Impact score (High, Medium, Low) |
| `source_timestamp` | TEXT | | Original publication timestamp |
| `system_timestamp` | TEXT | | Ingestion system timestamp |
| `enriched_at` | TEXT | | Timestamp of LLM enrichment |

### Table: `company_mentions`
Chronological aggregate of company discussions.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `company` | TEXT | PRIMARY KEY (with date) | Resolved ticker symbol |
| `date` | TEXT | PRIMARY KEY (with company) | Date of mention (YYYY-MM-DD) |
| `mentions` | INTEGER | | Count of mentions on this date |

### Table: `theme_velocity`
Saves Z-scores and rolling baselines of theme popularity.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `theme` | TEXT | PRIMARY KEY (with date) | Frozen theme name |
| `date` | TEXT | PRIMARY KEY (with theme) | Evaluation date |
| `mentions_today` | INTEGER | | Mentions count today |
| `avg_7d` | REAL | | 7-day rolling baseline average |
| `avg_30d` | REAL | | 30-day rolling baseline average |
| `z_score` | REAL | | Statistically normalized spike ratio |

### Table: `event_signals`
Calculated quantitative trade event signals.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique signal ID |
| `company` | TEXT | | Listed ticker symbol |
| `signal_date` | TEXT | | Date signal was triggered |
| `velocity` | REAL | | Mention velocity ratio |
| `today_mentions` | INTEGER | | Count of mentions today |
| `avg_mentions` | REAL | | 30-day baseline average mentions |
| `event_id` | INTEGER | | Foreign key referencing calendar event |
| `event_type` | TEXT | | Class (e.g., Board Meeting, Dividend) |
| `event_date` | TEXT | | Scheduled event date |
| `event_description`| TEXT | | Purpose/Description of the corporate event |
| `signal_strength` | TEXT | | Calculated power of signal (High/Medium/Low) |
| `created_at` | TEXT | | Timestamp when signal was generated |

### Table: `graph_nodes`
Maintains vertices in the structural Knowledge Graph.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique node ID |
| `node_name` | TEXT | UNIQUE NOT NULL | Node name (e.g., "Brent Crude") |
| `node_type` | TEXT | NOT NULL | Vertex type (e.g., Sector, Company, Geopolitical) |
| `symbol` | TEXT | | Listed company ticker symbol (if type='Company') |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Sync timestamp |

### Table: `graph_edges`
Defines directed, weighted relationships between graph nodes.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique edge ID |
| `source_node_id` | INTEGER | FK -> graph_nodes(id) ON DELETE CASCADE | Source node ID |
| `target_node_id` | INTEGER | FK -> graph_nodes(id) ON DELETE CASCADE | Target node ID |
| `relationship_type`| TEXT | NOT NULL | Relationship type (e.g., INPUT_OF, BENEFITS, HURTS) |
| `weight` | REAL | DEFAULT 1.0 | Connection weight |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Edge creation timestamp |

### Table: `impact_signals`
Calculated outputs of multi-depth macro event propagation.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Record ID |
| `article_id` | INTEGER | | Source article link ID |
| `event_type` | TEXT | NOT NULL | Ingested event category |
| `expectation_changed`| TEXT | NOT NULL | Shock class (e.g., Supply Shock, Pricing) |
| `first_order_node` | TEXT | NOT NULL | Initial node triggered |
| `target_company` | TEXT | NOT NULL | Downstream listed company name |
| `ticker` | TEXT | | Exchange symbol |
| `order_depth` | INTEGER | NOT NULL | Traversal depth (e.g. 2 for 2nd-order) |
| `direction` | TEXT | NOT NULL | Signal direction (BULLISH / BEARISH) |
| `conviction_score` | REAL | NOT NULL | Final options-adjusted conviction score |
| `magnitude_score` | REAL | NOT NULL | Traversal-decayed magnitude percentage |
| `signal_horizon` | TEXT | NOT NULL | Trade horizon |
| `pcr_level` | REAL | | Put-Call Ratio level at snapshot |
| `iv_percentile` | REAL | | Implied volatility percentile |
| `signal_date` | TEXT | NOT NULL | Event trigger date |
| `processed` | INTEGER | DEFAULT 0 | Execution status |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Signal generation timestamp |

---

## 🛢️ 2. Price Database: `price_data.db`

### Table: `price_history`
Maintains daily historical OHLCV pricing for listed companies and market benchmarks.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `symbol` | TEXT | PRIMARY KEY (with trade_date)| Exchange ticker symbol (e.g., `NIFTY50`) |
| `trade_date` | TEXT | PRIMARY KEY (with symbol) | Trade date (YYYY-MM-DD) |
| `open` | REAL | | Daily opening price |
| `high` | REAL | | Daily highest price |
| `low` | REAL | | Daily lowest price |
| `close` | REAL | | Daily closing price |
| `adj_close` | REAL | | Adjusted close price (split/dividend adjusted) |
| `volume` | INTEGER | | Daily trading volume |
| `created_at` | TEXT | | Sync timestamp |

### Table: `options_chain`
Maintains historical, strike-by-strike option chain snapshots for F&O listings.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `symbol` | TEXT | PRIMARY KEY (composite) | Underlying equity symbol |
| `expiry` | TEXT | PRIMARY KEY (composite) | Contract expiry date (YYYY-MM-DD) |
| `strike` | REAL | PRIMARY KEY (composite) | Strike price of option |
| `option_type` | TEXT | PRIMARY KEY (composite) | Contract type (CE = Call, PE = Put) |
| `ltp` | REAL | | Last Traded Price |
| `oi` | INTEGER | | Open Interest (contracts) |
| `change_in_oi` | INTEGER | | Daily change in Open Interest |
| `volume` | INTEGER | | Daily trading volume (contracts) |
| `implied_volatility`| REAL | | Implied Volatility (annualized %) |
| `underlying_price` | REAL | | Spot underlying price at snapshot |
| `snapshot_timestamp`| TEXT | PRIMARY KEY (composite) | Snapshot timestamp (YYYY-MM-DD HH:MM:SS) |
| `delta` | REAL | | Calculated Black-Scholes Delta |
| `gamma` | REAL | | Calculated Black-Scholes Gamma |
| `theta` | REAL | | Calculated Black-Scholes Theta |
| `vega` | REAL | | Calculated Black-Scholes Vega |
| `iv_percentile` | REAL | | Computed relative IV percentile |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

### Table: `options_summary`
Maintains rolled-up metrics (total Call/Put OI, volumes, and PCR) per symbol, expiry, and snapshot timestamp.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `symbol` | TEXT | PRIMARY KEY (composite) | Underlying symbol |
| `expiry` | TEXT | PRIMARY KEY (composite) | Contract expiry date (YYYY-MM-DD) |
| `snapshot_timestamp`| TEXT | PRIMARY KEY (composite) | Snapshot timestamp (YYYY-MM-DD HH:MM:SS) |
| `pcr` | REAL | | Put-Call Ratio (Put OI / Call OI) |
| `underlying_price` | REAL | | Spot underlying price |
| `total_call_oi` | INTEGER | | Sum call open interest |
| `total_put_oi` | INTEGER | | Sum put open interest |
| `total_call_volume` | INTEGER | | Sum call volume |
| `total_put_volume` | INTEGER | | Sum put volume |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |

---

## 🛢️ 3. Corporate Events Database: `corporate_events.db`

### Table: `board_meetings`
Tracks scheduled corporate board meetings.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Record ID |
| `company_symbol` | TEXT | | Company ticker symbol |
| `meeting_date` | TEXT | | Scheduled meeting date |
| `purpose` | TEXT | | Agenda/Purpose of the board meeting |
| `source` | TEXT | | Source (e.g., BSE Notice, RSS) |
| `guid` | TEXT | UNIQUE | Unique global ID to prevent duplicates |
| `created_at` | TEXT | | Sync timestamp |

*(Similar structures are defined for `corporate_events` and `financial_results` tables in this database).*
