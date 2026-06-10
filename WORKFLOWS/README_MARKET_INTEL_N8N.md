# MARKET_INTEL n8n Workflow

This pack creates this flow:

RSS Feed Read -> Limit -> Set -> OpenAI HTTP Request -> Parse AI JSON -> SQLite

## Files

- `market_intel_rss_ai_sqlite.workflow.json` - import this into n8n.
- `market_intel_schema.sql` - run once in SQLite to create the table.
- `market_intel_ai_prompt.txt` - prompt used by the AI step.

## Before Running

1. Create the SQLite database file:

   `D:\MARKET_INTEL\DATABASE\market_intel.db`

2. Run `market_intel_schema.sql` once on that database.

3. In n8n, import `market_intel_rss_ai_sqlite.workflow.json`.

4. Open the HTTP Request node named `AI - Analyze News`.

5. Add your OpenAI API key in the `Authorization` header:

   `Bearer YOUR_OPENAI_API_KEY`

6. Open the SQLite node and set database path:

   `D:\MARKET_INTEL\DATABASE\market_intel.db`

## RSS Feed

Default RSS feed:

`https://www.moneycontrol.com/rss/business.xml`

You can replace it in the first node.
