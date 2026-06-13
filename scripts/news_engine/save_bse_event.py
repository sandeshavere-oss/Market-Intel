import sys
import sqlite3
import re
from datetime import datetime
from pathlib import Path

# Setup shared logger
sys.path.append(str(Path(__file__).resolve().parent))
try:
    from logger_setup import get_logger
    logger = get_logger("save_bse_event.py")
except Exception as e:
    print(f"ERROR: Failed to import logging. {e}")
    sys.exit(1)

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "market_intel.db"

# Category patterns mapping
CATEGORY_PATTERNS = {
    "Financial Results": [
        r"quarterly results", r"q1 results", r"q2 results", r"q3 results", 
        r"q4 results", r"financial results", r"annual results", 
        r"unaudited results", r"audited results"
    ],
    "Board Meeting": [
        r"board meeting", r"board of directors", r"board meeting notice"
    ],
    "Shareholder Meeting": [
        r"agm", r"annual general meeting", r"egm", r"extraordinary general meeting",
        r"notice of agm", r"notice of egm"
    ],
    "Dividend": [
        r"dividend", r"interim dividend", r"final dividend", r"special dividend"
    ],
    "Buyback": [
        r"buyback", r"buy back", r"share repurchase"
    ],
    "M&A": [
        r"merger", r"acquisition", r"amalgamation", r"demerger", 
        r"scheme of arrangement", r"takeover", r"open offer"
    ],
    "Capital Raise": [
        r"qip", r"qualified institutional placement", r"fpo", r"follow-on",
        r"rights issue", r"ncd", r"non-convertible debentures"
    ],
    "Order Win": [
        r"order win", r"order received", r"contract awarded", 
        r"letter of intent", r"loi received", r"secured order", r"new order"
    ],
    "Regulatory": [
        r"insider trading", r"insider dealing", r"sast regulations", 
        r"substantial acquisition"
    ]
}

def classify_event_category(title):
    """Classifies the event category from the title using pattern matching."""
    title_lower = title.lower()
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, title_lower):
                return category
    return "General Announcement"

def main():
    # Try to parse base64 payload if a single arg is provided
    base64_payload = None
    if len(sys.argv) == 2:
        try:
            import base64
            import json
            decoded = base64.b64decode(sys.argv[1].encode('utf-8')).decode('utf-8')
            base64_payload = json.loads(decoded)
        except Exception as e:
            logger.warning(f"Failed to decode base64 argument: {e}")
            pass

    if base64_payload is not None:
        raw_article_id = base64_payload.get("article_id", "")
        raw_title = base64_payload.get("title", "")
        raw_company_name = base64_payload.get("company_name", "")
        raw_event_type = base64_payload.get("event_type", "")
        raw_sentiment = base64_payload.get("sentiment", "")
        raw_impact_score = base64_payload.get("impact_score", "5")
        raw_link = base64_payload.get("link", "")
        raw_published_at = base64_payload.get("published_at", "")
        raw_response = base64_payload.get("raw_response", "")
    else:
        if len(sys.argv) < 10:
            print("ERROR: Missing arguments. Expected 9 arguments.")
            logger.error(f"Execution failed: Expected 9 arguments, got {len(sys.argv) - 1}.")
            sys.exit(1)

        # Extract raw arguments
        raw_article_id = sys.argv[1]
        raw_title = sys.argv[2]
        raw_company_name = sys.argv[3]
        raw_event_type = sys.argv[4]
        raw_sentiment = sys.argv[5]
        raw_impact_score = sys.argv[6]
        raw_link = sys.argv[7]
        raw_published_at = sys.argv[8]
        raw_response = sys.argv[9]

    # Clean Inputs
    # 1. article_id & title
    article_id = raw_article_id.strip()
    title = raw_title.strip()

    # 2. company_name: strip whitespace and quotes
    company_name = raw_company_name.strip().strip('"').strip("'").strip()
    
    # 3. event_type: strip whitespace
    event_type = raw_event_type.strip()
    
    # 4. sentiment: must be in [Positive, Negative, Neutral, Unknown]
    sentiment = raw_sentiment.strip().capitalize()
    if sentiment not in ["Positive", "Negative", "Neutral", "Unknown"]:
        sentiment = "Unknown"
        
    # 5. impact_score: extract first integer, default to 5
    score_match = re.search(r'\d+', str(raw_impact_score))
    if score_match:
        try:
            impact_score = int(score_match.group(0))
        except ValueError:
            impact_score = 5
    else:
        impact_score = 5
        
    # 6. link & published_at
    link = raw_link.strip()
    published_at = raw_published_at.strip()
    
    # 7. Extract BSE Code from title if present (6-digit word)
    bse_code_match = re.search(r'\b\d{6}\b', title)
    bse_code = bse_code_match.group(0) if bse_code_match else ""

    # Determine Event Category
    event_category = classify_event_category(title)

    # Save to SQLite Database
    if not DB_PATH.exists():
        print(f"ERROR: Database file not found at {DB_PATH}")
        logger.error(f"Execution failed: Database file not found at {DB_PATH}")
        sys.exit(1)

    import time
    import random

    max_retries = 5
    retry_delay = 1.0
    success = False

    for attempt in range(max_retries):
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=60)
            conn.execute("PRAGMA journal_mode=WAL")
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR IGNORE INTO corporate_events
                (article_id, title, company_name, bse_code, event_type, event_category, 
                 sentiment, impact_score, link, published_at, raw_ollama_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article_id,
                    title,
                    company_name,
                    bse_code,
                    event_type,
                    event_category,
                    sentiment,
                    impact_score,
                    link,
                    published_at,
                    raw_response
                )
            )
            
            # Check if row was inserted or ignored as duplicate
            if cursor.rowcount == 0:
                print("DUPLICATE")
            else:
                conn.commit()
                print("SAVED")
            
            success = True
            break
            
        except sqlite3.OperationalError as ex:
            if "locked" in str(ex).lower() and attempt < max_retries - 1:
                sleep_time = retry_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                logger.warning(f"Database locked, retrying in {sleep_time:.2f}s (attempt {attempt+1}/{max_retries}). Error: {ex}")
                time.sleep(sleep_time)
            else:
                print(f"ERROR: Database write failed. {ex}")
                logger.error(f"Failed to insert event for article_id {article_id}: {ex}", exc_info=True)
                sys.exit(1)
        except Exception as ex:
            print(f"ERROR: Database write failed. {ex}")
            logger.error(f"Failed to insert event for article_id {article_id}: {ex}", exc_info=True)
            sys.exit(1)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
