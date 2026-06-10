# Market-Intel Development Roadmap

This document outlines the strategic roadmap for the **Market-Intel** platform, guiding its progression from a News Ingestion Tool to an Institutional-Grade Validated Signal Intelligence Platform.

---

## 📅 Roadmap Milestones

### Phase 1: Ingestion & Data Cleanup [Completed]
*   [x] Automated RSS feed scraping with deduplication rules.
*   [x] Exchange filing notice parsing (BSE notice crawler) with Playwright PDF extraction.
*   [x] Dual-timestamp ingestion (`source_timestamp` vs `system_timestamp`) to eliminate latency measurement error.
*   [x] Standardized Named Entity Resolution (NER) dictionary matching.

### Phase 2: Signal & Velocity Engines [Completed]
*   [x] Z-score calculation models for rolling theme and mention velocities.
*   [x] Logical unification of corporate events (UNION query joining events, meetings, results).
*   [x] Linear backtest validator executing trades on next-day Open price.
*   [x] Streamlit dashboard with custom CSS, multi-tab navigation, and Plotly analytics.

### Phase 3: Benchmark Outperformance & Alpha Isolation [In-Progress]
*   [/] Incremental Nifty 50 relative return calculator.
*   [ ] Event-Signal backtesting portfolio simulator.
*   [ ] Sector-neutral alpha adjustments.

### Phase 4: Saliency & Trend Detection [Planned]
*   [ ] **Topic Modelling & Sentiment Drift**: Moving beyond static keyword mapping to unsupervised topic tracking.
*   [ ] **Multi-Agent News Summarization**: Deploying local LLM agents to draft institutional executive summaries of complex events.
*   [ ] **Social Sentiment Integration**: Full scaling of Playwright session scrapers across quant communities on X/Twitter and Reddit.

---

## 📄 Future Research Paper Blueprint

Market-Intel is designed as a research-backed platform. Future research publications will focus on **"Event-Driven Alpha Isolation via Mention-Filings Convergence."**

```mermaid
graph LR
    A[Research Paper Concept] --> B[Technology Theme]
    B --> C[Required Components]
    C --> D[Listed Companies]
```

### 1. Technology Themes
*   **Theme**: *Natural Language Named Entity Resolution (NER) and Rolling Z-Score Velocity in Case-insensitive Indian Exchange Filings.*
*   **Thematic Focus**: Event-driven stock returns surrounding scheduled disclosures.

### 2. Required Components
To construct a publishable academic backtest, the following modules are required:
*   **Baseline Mention Estimator**: Resolves normal-day media conversation level.
*   **Slippage Simulator**: Mimics execution lags using next-day Open price (implemented).
*   **Benchmark Index Control Group**: Historical Nifty 50 daily price returns matched date-for-date with the signal dates (implemented).
*   **Sector Beta Adjuster**: Regressing returns against sector indices (e.g., NIFTY_IT, NIFTY_BANK) to isolate sector-neutral Alpha.

### 3. Target Listed Companies & Theme Mapping
The research focuses on the following primary listed companies mapped to key structural technology themes in India:

| Company Name | Exchange Ticker | Target Research Theme | Role in Pipeline |
| :--- | :--- | :--- | :--- |
| **Reliance Industries** | `RELIANCE.NS` | Green Energy / Retail Tech | Heavyweight index proxy |
| **Tata Motors** | `TATAMOTORS.NS`| Electric Vehicles (EV) | High-velocity event proxy |
| **Infosys** | `INFY.NS` | Artificial Intelligence (AI) | IT sector sentiment driver |
| **Tata Consultancy Services** | `TCS.NS` | Digital Infrastructure | IT sector baseline |
| **Larsen & Toubro** | `LT.NS` | Space Economy / Defence | Capital Goods proxy |
| **State Bank of India** | `SBIN.NS` | Capital Markets / Banking | BFSI sector proxy |