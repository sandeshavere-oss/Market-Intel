# Architecture Reference: MARKET_INTEL

This document outlines the system architecture, database relationships, workflow dependencies, and signal validation pipelines for the `MARKET_INTEL` platform.

---

## 1. System Architecture

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

## 2. Database Relationships

The system manages four separate SQLite databases, which are joined logically in the analytics and validation layers.

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
    EVENT_SIGNALS ||--|| SIGNAL_PERFORMANCE : "evaluates (one-to-one)"
    PRICE_HISTORY ||--o{ SIGNAL_PERFORMANCE : "supplies prices"
```,StartLine:163,TargetContent:
```

---

## 3. Workflow Dependencies

The execution pipeline must follow a specific logical order to ensure that signals are generated from fresh data and then validated.

```mermaid
stateDiagram-v2
    [*] --> IngestNews : Periodic
    [*] --> IngestBSE : Periodic
    [*] --> IngestTwitter : Periodic
    
    IngestNews --> ExtractKeywords
    IngestBSE --> SaveEvents
    IngestTwitter --> ProcessSentiment
    
    ExtractKeywords --> EnrichNews : Ollama Mistral:7b
    EnrichNews --> AggregateMentions
    EnrichNews --> CalculateThemeVelocity
    
    AggregateMentions --> GenerateSignals
    SaveEvents --> GenerateSignals : Check Board Meetings
    
    GenerateSignals --> LoadStockPrices : Trigger Price Fetch
    LoadStockPrices --> ValidateSignals : Calculate returns
    ValidateSignals --> UpdateDashboard
    
    UpdateDashboard --> [*]
```

---

## 4. Signal Ingestion & Processing Flow

This flowchart illustrates how a raw RSS article transforms into a validated quantitative trade signal shown on the Streamlit dashboard.

```mermaid
graph TD
    A[RSS News Feeds / BSE Notices]
    --> B[capture_rss.py / save_bse_event.py]
    --> C[(market_intel.db: keywords table)]
    --> D[company_match.py / Theme Mapping]
    --> E[theme_velocity.py / company_mentions]
    --> F[signal_engine.py / event_signals table]
    --> G[price_loader.py / price_history table]
    --> H[validate_signals.py / signal_performance table]
    --> I[dashboard.py / Streamlit Performance Tab]
```
