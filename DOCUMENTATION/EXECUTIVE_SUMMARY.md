# Executive Summary: MARKET_INTEL

## Project Overview
`MARKET_INTEL` is an automated quantitative intelligence and signal validation platform designed to convert raw market text (news RSS feeds, official regulatory filings, and targeted social media activity) into actionable, validated trading signals.

The system's core mission is to answer a single critical question: **"Can this system generate signals that outperform the market?"**

To do this, the platform has transitioned from a standard *News Intelligence Platform* (categorizing and sentiment-tagging articles) to a *Validated Signal Intelligence Platform* (measuring the actual forward performance of stocks following specific corporate events and news spikes).

---

## System Architecture & Pipeline
The system operates as a data pipeline with five distinct layers:
1.  **Ingestion Layer:** Playwright-based web crawlers and RSS parsers ingest news feeds, BSE notices, and targeted Twitter handles.
2.  **AI Analysis Layer:** A local LLM (Ollama Mistral:7b) performs entity extraction, sentiment analysis, impact scoring, and standardizes categorization to 16 frozen themes.
3.  **Analytics & Signal Layer:** The system tracks daily entity mention velocity. It triggers a convergence signal when a stock's mention velocity spikes (>2.5x the 30-day average) and coincides with an upcoming board meeting (within a 7-day window).
4.  **Backtest Validation Layer:** Incremental price loaders fetch daily stock price data from Yahoo Finance. The backtest return engine calculates absolute 5-day and 10-day forward returns starting from the next-day Open price (to eliminate look-ahead bias).
5.  **Presentation Layer:** A Streamlit dashboard displays real-time signal metrics, performance statistics (win rates, best/worst trades, returns), and raw feed tracking.

---

## Current Status & Roadmap
*   **Progress:** The core pipeline, signal generation, incremental price loader, validation engine, and Streamlit dashboard are 100% functional.
*   **Next Priority:** Normalizing forward returns against the Nifty 50 index to isolate pure market-neutral outperformance ($\alpha$).
*   **Risk Mitigation:** The platform uses a local sqlite-backed structure, separated into four databases to prevent write locks, and runs all scraping workflows asynchronously via n8n.
