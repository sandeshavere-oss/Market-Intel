import sqlite3
import json
import logging
import urllib.request
import urllib.error
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path

# Setup Logging via shared module
sys.path.append(str(Path(__file__).resolve().parent))
from logger_setup import get_logger
logger = get_logger("generate_daily_intel.py")

# Resolve Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "market_intel.db"
OLLAMA_URL = "http://localhost:11434/api/generate"

def query_ollama_synthesis(articles_text):
    """Queries local Ollama (Mistral 7B) to synthesize the daily market intelligence brief."""
    prompt = f"""You are a Principal Market Intelligence Architect. Synthesize a professional market intelligence briefing based on the following list of news and announcements processed in the last 24 hours.

Articles:
{articles_text}

Perform the following tasks:
1. Synthesize the top active market themes and their momentum.
2. Identify emerging themes or signals.
3. Identify top mentioned companies and summarize their disclosures.
4. Highlight the most important corporate events (mergers, dividend announcements, splits).
5. Write a comprehensive narrative daily market intelligence briefing.

Return EXACTLY a JSON block with the following structure:
{{
  "top_themes": "- Theme A: description\\n- Theme B: description",
  "top_companies": "- Company A: description\\n- Company B: description",
  "important_events": "- Event A: description\\n- Event B: description",
  "raw_summary": "### Daily Market Intelligence Brief\\n\\nDetailed professional briefing in Markdown format..."
}}

Rules:
- Output ONLY the JSON block. Do not include markdown blocks (like ```json) or any other text.
"""
    payload = {
        "model": "mistral:7b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 800,
            "num_ctx": 4096
        }
    }
    
    try:
        req = urllib.request.Request(
            OLLAMA_URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=900) as response:
            result = json.loads(response.read().decode('utf-8'))
            raw_response = result.get("response", "").strip()
            
            # Clean up potential markdown formatting
            raw_response = re.sub(r"^```json\s*", "", raw_response)
            raw_response = re.sub(r"\s*```$", "", raw_response)
            raw_response = raw_response.strip()
            
            # Find JSON block boundaries
            start = raw_response.find('{')
            end = raw_response.rfind('}') + 1
            if start != -1 and end != 0:
                raw_response = raw_response[start:end]
                
            data = json.loads(raw_response)
            return {
                "top_themes": data.get("top_themes", "").strip(),
                "top_companies": data.get("top_companies", "").strip(),
                "important_events": data.get("important_events", "").strip(),
                "raw_summary": data.get("raw_summary", "").strip()
            }
    except Exception as e:
        logger.error(f"Failed to query Ollama for synthesis: {e}")
        return None

def main():
    if not DB_PATH.exists():
        logger.error(f"Database file not found at {DB_PATH}. Exiting.")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Fetch articles from the last 24 hours
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Querying processed articles since: {yesterday}")
    
    cursor.execute("""
        SELECT title, related_companies, theme, keywords, created_at, raw_text
        FROM keywords
        WHERE processed = 1
          AND datetime(created_at) >= ?
        ORDER BY id DESC
        LIMIT 15
    """, (yesterday,))
    rows = cursor.fetchall()
    
    # Fallback to last 15 processed articles if less than 5 exist in last 24 hours (ensures testability)
    if len(rows) < 5:
        logger.info(f"Only {len(rows)} articles found in the last 24 hours. Falling back to the 15 most recent processed articles for synthesis.")
        cursor.execute("""
            SELECT title, related_companies, theme, keywords, created_at, raw_text
            FROM keywords
            WHERE processed = 1
            ORDER BY id DESC
            LIMIT 15
        """)
        rows = cursor.fetchall()
        
    if not rows:
        logger.warning("No processed articles available in the database to synthesize. Exiting.")
        conn.close()
        return 0
        
    logger.info(f"Aggregating {len(rows)} articles for daily briefing...")
    
    # Format articles for prompt (exluding raw text to keep context compact and prevent timeouts)
    articles_list = []
    for idx, row in enumerate(rows, 1):
        title, companies, themes, keywords, created, text = row
        articles_list.append(
            f"Article #{idx}:\n"
            f"- Title: {title}\n"
            f"- Companies: {companies}\n"
            f"- Themes: {themes}\n"
            f"- Keywords: {keywords}\n"
            f"- Date: {created}\n"
        )
        
    formatted_articles = "\n---\n".join(articles_list)
    
    # Query Ollama to generate daily summary
    logger.info("Sending aggregated articles to Ollama for trend synthesis...")
    brief = query_ollama_synthesis(formatted_articles)
    
    if not brief:
        logger.error("Synthesis failed. No summary saved.")
        conn.close()
        sys.exit(1)
        
    # Store daily summary (INSERT OR REPLACE)
    summary_date = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Saving daily intelligence summary for date: {summary_date}...")
    
    try:
        cursor.execute(
            """
            INSERT OR REPLACE INTO daily_intelligence
            (summary_date, top_themes, top_companies, important_events, raw_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                summary_date,
                brief["top_themes"],
                brief["top_companies"],
                brief["important_events"],
                brief["raw_summary"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        conn.commit()
        logger.info("Daily intelligence briefing saved successfully!")
        return len(rows)
    except Exception as e:
        logger.error(f"Failed to save summary to database: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Script started")
    try:
        processed_count = main()
        logger.info(f"Completed. {processed_count} articles processed")
    except Exception as e:
        logger.error(f"FATAL: {str(e)}", exc_info=True)
        sys.exit(1)
