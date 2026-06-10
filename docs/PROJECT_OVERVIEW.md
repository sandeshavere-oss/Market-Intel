# Project Overview: Market-Intel

Market-Intel is an advanced, quantitative news and event intelligence system designed to isolate and trade on informational Alpha ($\alpha$). By cross-referencing real-time news velocity spikes with official corporate event calendars (board meetings, financial disclosures, corporate announcements), Market-Intel generates high-conviction signals that seek to outperform the market benchmark.

---

## 💡 The Core Value Proposition

Traditional market sentiment indicators rely on simple keyword count aggregates, which suffer from a high noise-to-signal ratio. Market-Intel introduces a dual-factor validation model:
1.  **Mention Velocity Spikes**: Measures exponential surges in discussion relative to baseline historical averages (using rolling Z-scores).
2.  **Corporate Event Convergence**: Cross-references these spikes with hard corporate calendar dates (from exchange filing scrapers) to validate whether the noise represents a structural market event.

By merging unstructured media narratives with structured corporate filings, the system eliminates look-ahead bias and filters out non-actionable market noise, creating a robust framework for event-driven quantitative trading.

---

## 🔍 Core Methodologies

### 1. Company Mention Tracking
Market-Intel tracks entity mentions by scanning unstructured news articles and social media feeds (e.g., RSS Feeds, Twitter/X) and resolving company references to standard exchange ticker symbols.
*   **Deterministic Matching**: Uses a curated dictionary (`company_master.csv`) of primary exchange listings, symbols, and common aliases.
*   **Regex Word Boundaries**: Compiles high-performance regex patterns to isolate ticker references (e.g., resolving "Reliance" or "RELIANCE" to `RELIANCE.NS`).
*   **Enrichment Fail-safe**: When deterministic matching fails or is ambiguous, the system forwards the text to a local LLM (Ollama Mistral:7b) to perform named entity resolution (NER) and map mentions back to standard listings.

### 2. Velocity Detection Engine
To identify when a stock is experiencing abnormal news flow, the system computes the **Mention Velocity** for each symbol:
$$\text{Mention Velocity} = \frac{\text{Mentions Today}}{\text{Average Mentions (30-day baseline)}}$$
*   **Baseline Calibration**: The system maintains a historical rolling record of company mentions. If a company usually has 1 mention per day but suddenly receives 10 mentions, the velocity spike ratio is $10.0$.
*   **Theme Z-Scores**: The system tracks theme velocity similarly, computing Z-scores on theme ingestion counts over a 7-day and 30-day average. This highlights sector-level thematic rotations.

### 3. Theme Mapping and Detection
Rather than allowing endless taxonomy drift, the system operates on **16 Frozen Core Themes** (such as AI, Semiconductor, EV, Defence, Space Economy, Green Energy, Digital Infrastructure). 
*   **Deterministic Themes**: Resolves theme associations via `theme_mapping.csv` based on keyword occurrences.
*   **Standardization Pipeline**: Emerging themes detected by LLMs are standardized via a fuzzy-match ontology mapping. If a theme does not map to one of the 16 core themes, it is added to a `theme_backlog.csv` for human review rather than polluting the live databases.

### 4. Convergence and Signal Generation
A raw mention velocity spike does not trigger a trade signal by itself. A signal is generated only when the spike **converges** with a scheduled corporate event:
*   **Table Unification**: A unified SQLite view aggregates upcoming board meetings, financial disclosures, and event calendars.
*   **Convergence Window**: If a company's mention velocity spikes within a predefined window of an official meeting or disclosure, the system registers an `EVENT_SIGNAL` and classifies its strength (High, Medium, Low) based on sentiment and spike amplitude.

---

## 📈 Backtest & Performance Validation
All signals generated are audited by the **Validation Engine**:
*   **Entry Pricing**: Simulates entry on the **next-day Open price** rather than the signal-day Close, entirely eliminating look-ahead and execution bias.
*   **Holding Periods**: Measures exact returns over 5-day and 10-day holding intervals.
*   **Benchmark Relative Returns**: Normalizes returns against the Nifty 50 benchmark over the identical period to isolate pure **Alpha ($\alpha$)** from market beta ($\beta$).
