import os
import sys
import sqlite3
import json
import logging
import requests
import re
from pathlib import Path
from datetime import datetime

# Resolve base paths dynamically
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "DATABASE" / "twitter_intel.db"
LOG_DIR = BASE_DIR / "LOGS"
LOG_FILE = LOG_DIR / "twitter_engine.log"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
# Add console logging
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)

def init_db():
    logging.info(f"Initializing Twitter database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if tweets table exists and has impact column
        cursor.execute("PRAGMA table_info(tweets)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if columns and "impact" not in columns:
            logging.info("Old tweets schema detected. Dropping table to upgrade.")
            cursor.execute("DROP TABLE tweets")
            columns = []
            
        if not columns:
            # Create tweets table with impact column
            cursor.execute("""
                CREATE TABLE tweets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    twitter_handle TEXT,
                    tweet_text TEXT,
                    tweet_url TEXT UNIQUE,
                    sentiment TEXT,
                    impact TEXT,
                    created_at TEXT
                )
            """)
            logging.info("Created tweets table with impact column.")
            
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)

def fallback_sentiment(text: str) -> str:
    text_lower = text.lower()
    
    pos_words = ["gain", "rise", "jump", "surge", "soar", "profit", "growth", "approved", "up", "bull", "buy", "win", "high", "success", "expand", "positive", "love", "great", "awesome", "excellent", "bullish", "amazing", "strides", "good", "impressive", "strong", "perfect", "better", "best", "wonderful", "cool", "fantastic", "proud"]
    neg_words = ["loss", "fall", "crash", "slump", "drop", "decline", "down", "bear", "sell", "debt", "investigate", "fine", "cut", "weak", "concern", "negative", "hate", "bad", "worst", "fail", "bearish", "poor", "terrible", "awful", "worse", "disappointing", "critical"]
    
    pos_score = sum(1 for w in pos_words if w in text_lower)
    neg_score = sum(1 for w in neg_words if w in text_lower)
    
    if pos_score > neg_score:
        return "Positive"
    elif neg_score > pos_score:
        return "Negative"
    return "Neutral"

def fallback_impact(text: str) -> str:
    text_lower = text.lower()
    
    high_words = ["billion", "crore", "lakh cr", "policy", "rate cut", "rate hike", "sebi", "rbi", "merger", "acquisition", "ipo", "crash", "surge", "historic", "record", "shares crash", "slumps"]
    medium_words = ["earnings", "quarter", "results", "announcement", "stake", "order", "contract", "launch", "deals", "profit", "growth"]
    
    high_score = sum(1.5 for w in high_words if w in text_lower)
    med_score = sum(1.0 for w in medium_words if w in text_lower)
    
    if high_score > 2.0:
        return "High"
    elif high_score + med_score > 0.5:
        return "Medium"
    return "Low"

def query_ollama_analysis(text: str) -> dict:
    url = "http://localhost:11434/api/generate"
    prompt = f"""Analyze the market sentiment and impact of this tweet.
Tweet: "{text}"

Return EXACTLY a JSON block with keys:
{{
  "sentiment": "Positive" | "Negative" | "Neutral",
  "impact": "High" | "Medium" | "Low"
}}

Rules:
- Output ONLY valid JSON, no markdown, no other text outside the JSON block.
"""
    
    payload = {
        "model": "mistral:7b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=180)
        if response.status_code == 200:
            raw_text = response.json().get("response", "").strip()
            # Clean potential markdown block formatting
            raw_text = re.sub(r"^```json\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)
            data = json.loads(raw_text)
            
            # Standardize capitalization
            sent = data.get("sentiment", "Neutral").strip().capitalize()
            imp = data.get("impact", "Low").strip().capitalize()
            
            if sent not in ["Positive", "Negative", "Neutral"]:
                sent = "Neutral"
            if imp not in ["High", "Medium", "Low"]:
                imp = "Low"
                
            return {"sentiment": sent, "impact": imp}
    except Exception as e:
        logging.warning(f"Ollama sentiment/impact query failed: {e}. Using fallback.")
        
    return None

def cleanup_old_tweets(conn):
    logging.info("Running auto-cleanup of tweets older than 30 days...")
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tweets WHERE datetime(created_at) < datetime('now', '-30 days')")
        deleted_rows = cursor.rowcount
        if deleted_rows > 0:
            logging.info(f"Purged {deleted_rows} old tweets from database.")
        else:
            logging.info("No old tweets to purge.")
    except Exception as e:
        logging.error(f"Failed to cleanup old tweets: {e}")

def save_tweet(payload_dict: dict):
    handle = payload_dict.get("twitter_handle", "").strip()
    text = payload_dict.get("tweet_text", "").strip()
    url = payload_dict.get("tweet_url", "").strip()
    created_at = payload_dict.get("created_at", "").strip()
    
    if not text:
        logging.error("Empty tweet text. Ingestion skipped.")
        return
        
    if not url:
        logging.warning("Missing tweet_url. Generating unique hash link.")
        url = f"https://twitter.com/unknown/status/{hash(text + handle)}"
        
    if not created_at:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check uniqueness
    cursor.execute("SELECT 1 FROM tweets WHERE tweet_url = ?", (url,))
    if cursor.fetchone():
        logging.info(f"Duplicate tweet detected (URL: {url}). Skipping.")
        conn.close()
        return
        
    # Analyze sentiment and impact
    logging.info(f"Analyzing sentiment and impact for tweet by @{handle}...")
    analysis = query_ollama_analysis(text)
    
    if analysis:
        sentiment = analysis["sentiment"]
        impact = analysis["impact"]
    else:
        sentiment = fallback_sentiment(text)
        impact = fallback_impact(text)
        
    logging.info(f"Determined sentiment: {sentiment} | Impact: {impact}")
    
    try:
        cursor.execute(
            """
            INSERT INTO tweets (twitter_handle, tweet_text, tweet_url, sentiment, impact, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (handle, text, url, sentiment, impact, created_at)
        )
        conn.commit()
        logging.info(f"Successfully saved tweet from @{handle} (ID: {cursor.lastrowid})")
        
        # Run cleanup
        cleanup_old_tweets(conn)
        conn.commit()
    except Exception as e:
        logging.error(f"Error inserting tweet into database: {e}", exc_info=True)
    finally:
        conn.close()

def main():
    init_db()
    
    payload_str = ""
    
    if len(sys.argv) > 1:
        payload_str = sys.argv[1]
    else:
        if not sys.stdin.isatty():
            payload_str = sys.stdin.read()
            
    if not payload_str.strip():
        logging.error("No JSON payload received via arguments or stdin.")
        print("Error: Missing JSON payload.", file=sys.stderr)
        sys.exit(1)
        
    try:
        payload_dict = json.loads(payload_str)
    except Exception as e:
        logging.error(f"Failed to parse JSON payload: {e}")
        print(f"Error: Invalid JSON payload. {e}", file=sys.stderr)
        sys.exit(1)
        
    if isinstance(payload_dict, list):
        logging.info(f"Processing batch of {len(payload_dict)} tweets.")
        for item in payload_dict:
            save_tweet(item)
    elif isinstance(payload_dict, dict):
        save_tweet(payload_dict)
    else:
        logging.error("Invalid payload type. Expected JSON object or list.")
        sys.exit(1)

if __name__ == "__main__":
    main()
