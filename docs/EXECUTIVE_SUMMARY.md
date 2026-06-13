# Executive Summary: MARKET_INTEL

## Project Overview
`MARKET_INTEL` is an automated quantitative intelligence and signal validation platform designed to convert raw market text (news RSS feeds, official regulatory filings, and targeted social media activity) into actionable, validated trading signals.

The system's core mission is to answer a single critical question: **"Can this system generate signals that outperform the market?"**

To do this, the platform has transitioned from a standard *News Intelligence Platform* (categorizing and sentiment-tagging articles) to a *Validated Signal Intelligence Platform* (measuring the actual forward performance of stocks following specific corporate events and news spikes).

---

## System Architecture & Pipeline
The system operates as a data pipeline with six distinct layers:
1.  **Ingestion Layer:** Playwright crawlers, RSS pollers, and a headful option chain scraper ingest news feeds, filings, Twitter handles, and NSE option chains.
2.  **AI Analysis Layer:** A local LLM (Ollama Mistral:7b) performs entity extraction, sentiment analysis, and standardizes categories to 16 frozen themes.
3.  **Knowledge Graph Layer:** Upstream/downstream nodes are linked with weighted relationships (BENEFITS, HURTS, INPUT_OF) to model systemic, multi-depth impact propagation.
4.  **Options Greeks Layer:** Computes standard Greeks (Delta, Gamma, Vega, Theta), Put-Call Ratios, and relative IV percentiles to confirm or discount signals.
5.  **Backtest Validation Layer:** Incremental price loaders fetch daily data from Yahoo Finance and calculate 5d/10d forward returns starting from the next-day Open price.
6.  **Presentation Layer:** A Streamlit dashboard displays real-time signal metrics, performance statistics, and historical results.

---

## Current Status & Roadmap
*   **Progress:** The Market Impact Propagation Engine (v4.0) and Options Greeks Layer (v2.1 scoring) are 100% complete and verified against 83 historical candidates.
*   **Next Priority:** Normalizing forward returns against the Nifty 50 index to isolate pure market-neutral outperformance ($\alpha$).
*   **Risk Mitigation:** SQLite databases use WAL mode to prevent file locks, and options scoring discounts pre-event signals when implied volatility is elevated to protect against post-event IV crush.
