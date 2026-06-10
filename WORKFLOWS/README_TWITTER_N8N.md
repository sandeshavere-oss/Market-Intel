# Twitter Ingestion Pipeline n8n Integration Guide

This guide details how to import, test, and execute the automated Twitter/X feed ingestion pipeline using n8n and our secure headless cookie fetcher.

---

## 🛠️ Step 1: Pre-requisites & Local Testing

Before setting up n8n, make sure you have generated the browser session cookies. 

1. **Log in to x.com**: Log in manually on your normal desktop browser.
2. **Export Cookies**: Use a cookie-exporting browser extension (e.g. *EditThisCookie* or *Get cookies.txt LOCALLY*) to export cookies as a JSON array.
3. **Save**: Save this JSON inside the workspace as:
   `D:\MARKET_INTEL\SOCIAL_ENGINE\raw_cookies.json`
4. **Convert to Playwright Format**: Run the conversion script to format them for Playwright:
   ```bash
   python SOCIAL_ENGINE/convert_cookies.py
   ```
   *(Verify that the file `D:\MARKET_INTEL\SOCIAL_ENGINE\twitter_cookies.json` was generated)*
5. **Test the Pipeline Manually**: Open a terminal in the root workspace `D:\MARKET_INTEL` and run:
   ```bash
   python SOCIAL_ENGINE/fetch_tweets.py | python SOCIAL_ENGINE/save_tweets.py
   ```
   Check that it logs `Fetcher completed. Parsed X tweets` and inserts them successfully into the database.

---

## ⚙️ Step 2: Import & Setup Workflow in n8n

The preconfigured n8n workflow file is located at `D:\MARKET_INTEL\WORKFLOWS\twitter_ingestion.json`.

1. **Open your n8n Dashboard** in your browser.
2. **Import Workflow**:
   * Click on **Workflows** in the sidebar.
   * Click on **Add Workflow** (or **New**).
   * Click the **three dots menu (top right)** and select **Import from File**.
   * Choose the file: `D:\MARKET_INTEL\WORKFLOWS\twitter_ingestion.json`.
3. **Review the Nodes**:
   * **When clicking "Execute Workflow"**: Allows manual runs.
   * **Schedule Trigger**: Triggers the flow every 1 hour (you can change this interval as desired).
   * **Execute Ingestion Pipeline**: Runs the command:
     `python "D:\MARKET_INTEL\SOCIAL_ENGINE\fetch_tweets.py" | python "D:\MARKET_INTEL\SOCIAL_ENGINE\save_tweets.py"`

---

## 🔬 Step 3: Test and Run inside n8n

1. Click **Listen for test event** or click the **Execute Workflow** button at the bottom of the n8n editor.
2. n8n will run the Python script command on your local system.
3. Once the workflow turns green:
   * It means the command was executed successfully.
   * It automatically fetched the timeline headlessly, refreshed the cookie session state on disk, analyzed sentiments/impacts via local Ollama, and stored unique entries in the SQLite database.
4. **Monitor Logs**: If any errors occur, they will be logged to:
   `D:\MARKET_INTEL\LOGS\twitter_engine.log`
5. **Toggle Active**: Once tested successfully, toggle the workflow state to **Active** in n8n to enable the hourly background scraping!
