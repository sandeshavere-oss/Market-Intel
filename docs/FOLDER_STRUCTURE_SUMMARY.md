# Folder Structure Summary: MARKET_INTEL

This document serves as a directory guide for the `MARKET_INTEL` workspace. It describes the purpose of each subdirectory and the key scripts contained within them.

```text
D:/MARKET_INTEL/
├── .env                              # API keys, database paths, and environment settings
├── dashboard.py                      # Main Streamlit web dashboard app
├── context.md                        # Project roles, goals, and preferred output styles
├── MARKET_INTEL_ROADMAP.md           # High-level checklist of project phases
│
├── AUDIT/                            # Logs of unclassified articles for manual review
├── BACKUP/                           # Historical snapshots and code backups
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
├── LOGS/                             # Runtime log output folder for engines and cron tasks
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
