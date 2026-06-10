# Market-Intel: Validated Signal Intelligence Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Database: SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Streamlit: UI](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)

Market-Intel is an end-to-end, AI-powered quant intelligence platform that ingests news, financial disclosures, and social media signals to detect high-conviction events. It automates the ingestion, local LLM enrichment, signal validation, and return backtesting against real historical stock data, displaying outcomes in a dynamic Streamlit dashboard.

---

## 🚀 Primary Objective
> **"Can this system generate signals that outperform the market?"**
> Market-Intel seeks to isolate pure Alpha ($\alpha$) by tracking mention velocity spikes, correlating them with scheduled corporate events (board meetings, earnings calls, financial disclosures), and benchmarking their performance against the Nifty 50 index.

---

## 🏛️ System Architecture

The platform uses a layered architecture, decoupling ingestion, database storage, analysis, and presentation.

```mermaid
graph TD
    %% Ingestion Layer
    subgraph Ingestion Layer
        RSS[RSS Feeds]
        BSE[BSE Notices API]
        Twitter[Twitter Crawlers]
    end

    %% Processing Layer
    subgraph Processing Layer
        CRSS[capture_rss.py]
        CBSE[save_bse_event.py]
        CTWT[save_tweets.py]
        ENR[enrich_news.py / Ollama Mistral:7b]
    end

    %% Database Layer
    subgraph Database Layer
        DB_MI[(market_intel.db)]
        DB_PR[(price_data.db)]
        DB_CP[(corporate_events.db)]
        DB_TW[(twitter_intel.db)]
    end

    %% Analytics & Validation Layer
    subgraph Analytics & Validation Layer
        VEL[theme_velocity.py]
        MNT[mention_engine.py]
        SIG[signal_engine.py]
        PRC[price_loader.py]
        VAL[validate_signals.py]
    end

    %% Presentation Layer
    subgraph Presentation Layer
        DASH[dashboard.py / Streamlit]
    end

    %% Data Flows
    RSS --> CRSS
    BSE --> CBSE
    Twitter --> CTWT

    CRSS --> DB_MI
    CBSE --> DB_CP
    CBSE --> DB_MI
    CTWT --> DB_TW

    DB_MI --> ENR --> DB_MI

    DB_MI --> MNT
    DB_MI --> VEL
    DB_CP --> SIG
    MNT --> SIG
    VEL --> SIG
    
    SIG --> DB_MI
    
    DB_PR --> VAL
    DB_MI --> VAL --> DB_MI
    
    PRC --> DB_PR

    DB_MI --> DASH
    DB_PR --> DASH
    DB_CP --> DASH
    DB_TW --> DASH
```

---

## 📂 Repository Structure

The project directory is structured as follows:

```text
D:/MARKET_INTEL/
├── .env                              # API keys, database paths, and environment settings
├── .gitignore                        # Git exclusions for secrets, caches, and databases
├── dashboard.py                      # Main Streamlit web dashboard app
├── context.md                        # Project roles, goals, and preferred output styles
├── MARKET_INTEL_ROADMAP.md           # High-level checklist of project phases
│
├── AUDIT/                            # Logs of unclassified articles for manual review
├── BACKUP/                           # Historical snapshots and code backups (ignored in Git)
│
├── CORPORATE_ENGINE/                 # BSE parsing and corporate filings logic
│   └── save_corp_data.py             # Parses and saves incoming corporate filing data
│
├── DATABASE/                         # SQLite storage layer (split to prevent file locks)
│   ├── market_intel.db               # Main database for news, mentions, velocities, signals
│   ├── price_data.db                 # Historical daily price bars (OHLCV + Adj Close)
│   ├── corporate_events.db           # Official board meetings, results, and disclosures
│   └── twitter_intel.db              # Scraped social media tweets and sentiment tags
│
├── DOCUMENTATION/                    # Centralized knowledge base
│   ├── ARCHITECTURE.md               # Architecture details, ER diagrams, workflows
│   ├── CHANGELOG.md                  # Release log following "Keep a Changelog" format
│   ├── DATABASE_SCHEMA.md            # Database columns, keys, and row counts
│   ├── DECISIONS.md                  # Strategic decision records (Decision -> Reason -> Impact)
│   ├── PROJECT_AUDIT.md              # Detailed file, schema, and workflow audit report
│   ├── PROJECT_STATUS.md             # Development checklists and layer completion boards
│   ├── ROADMAP.md                    # Strategic sprints, goals, ROI tasks, and risk registers
│   └── SESSION_SUMMARY.md            # Chronological run history and log summaries
│
├── LOGS/                             # Runtime log outputs (ignored in Git)
│
├── MAPPINGS/                         # Entity-to-symbol and keyword-to-theme mappings
│   ├── company_master.csv            # Maps company names and variations to exchange tickers
│   └── theme_mappings.csv            # Dictates keyword mappings to the 16 frozen themes
│
├── NEWS_ENGINE/                      # RSS collection and AI enrichment engines
│   ├── capture_rss.py                # Periodically pulls articles and writes raw keywords
│   ├── company_match.py              # Scans texts and resolves mentions to ticker symbols
│   ├── enrich_news.py                # Connects to local Ollama LLM to tag sentiment and impact
│   ├── migration.py                  # Script to inject dual timestamps (source vs system)
│   └── save_keywords.py              # Core insertion script for raw articles
│
├── PRICE_ENGINE/                     # Historical stock price loader
│   └── price_loader.py               # Fetches daily historical Yahoo Finance prices incrementally
│
├── SIGNAL_ENGINE/                    # Signal calculation and outcome validator scripts
│   └── validate_signals.py           # Quantitative backtester checking 5d/10d holds from next-day Open
│
├── SOCIAL_ENGINE/                    # Playwright scraper scripts for social media
│   ├── convert_cookies.py            # Utility to convert browser cookie formats
│   └── save_tweets.py                # Crawls target social accounts using cookies
│
└── WORKFLOWS/                        # JSON blueprints for n8n orchestrations
    ├── bse_ingestion.json            # n8n notice scraper trigger
    ├── capture_workflow.json         # RSS feed poller trigger
    ├── daily_briefing_workflow.json  # Runs daily summary briefings
    ├── enrichment_workflow.json      # Triggers Ollama enrichment calls
    └── twitter_ingestion.json        # Twitter playwright cron trigger
```

---

## 🛢️ Database Schema & Relationships

The system manages four separate SQLite databases, which are joined logically in the analytics and validation layers:

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

    %% corporate_events.db
    CORPORATE_EVENTS {
        int id PK
        string company_symbol
        string event_date
        string event_type
        string description
        string source
        string guid
        datetime created_at
    }

    BOARD_MEETINGS {
        int id PK
        string company_symbol
        string meeting_date
        string purpose
        string source
        string guid
        datetime created_at
    }

    FINANCIAL_RESULTS {
        int id PK
        string company_symbol
        string quarter
        string financial_year
        float revenue
        float net_profit
        string outcome_summary
        string guid
        datetime created_at
    }

    %% In-Memory or Logical Joins
    KEYWORDS ||--o{ COMPANY_MENTIONS : "aggregates to"
    KEYWORDS ||--o{ THEME_VELOCITY : "aggregates to"
    COMPANY_MENTIONS ||--o{ EVENT_SIGNALS : "triggers"
    CORPORATE_EVENTS ||--o{ EVENT_SIGNALS : "validates"
    BOARD_MEETINGS ||--o{ EVENT_SIGNALS : "validates"
    FINANCIAL_RESULTS ||--o{ EVENT_SIGNALS : "validates"
    EVENT_SIGNALS ||--|| SIGNAL_PERFORMANCE : "evaluates"
    PRICE_HISTORY ||--o{ SIGNAL_PERFORMANCE : "supplies prices"
```

---

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/sandeshavere-oss/Market-Intel.git
cd Market-Intel
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
X_USERNAME=your_x_username
X_PASSWORD=your_x_password
X_EMAIL=your_x_email
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Make sure to run playwright install if using the Twitter scraper)*
```bash
playwright install
```

### 4. Run Streamlit Dashboard
```bash
streamlit run dashboard.py
```

---

## 🔄 Run Pipelines

Data collection and enrichment pipelines are orchestrated via the `WORKFLOWS/*.json` n8n definitions, or can be triggered manually:
1. **RSS Ingestion:** Run `python NEWS_ENGINE/capture_rss.py`.
2. **AI Enrichment:** Run `python NEWS_ENGINE/enrich_news.py` (requires local Ollama server running `mistral:7b` or your chosen model).
3. **Price Fetcher:** Run `python PRICE_ENGINE/price_loader.py`.
4. **Signal Engine:** Run `python NEWS_ENGINE/signal_engine.py` or equivalent signal calculations.
5. **Backtest/Validation:** Run `python SIGNAL_ENGINE/validate_signals.py` to evaluate outcome performance.
