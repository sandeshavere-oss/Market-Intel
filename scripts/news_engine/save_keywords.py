import sqlite3
import sys
import logging
from datetime import datetime
from pathlib import Path
import csv
import io
import re
import urllib.request
import urllib.error
import json
from pypdf import PdfReader

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Dynamic base path resolution relative to this script
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "market_intel.db"
MAPPING_FILE = BASE_DIR / "data" / "mappings" / "company_mapping.csv"
THEME_FILE = BASE_DIR / "data" / "mappings" / "theme_mapping.csv"

OLLAMA_URL = "http://localhost:11434/api/generate"

EVENT_TYPES = [
    "Listing",
    "Bonus Issue",
    "Stock Split",
    "Suspension",
    "Delisting",
    "Rights Issue",
    "Board Meeting",
    "Record Date",
    "Dividend",
    "Merger",
    "Amalgamation"
]

def download_pdf(url):
    """Downloads PDF from the given URL."""
    logger.info(f"Downloading PDF from: {url}")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                return response.read()
    except Exception as e:
        logger.error(f"Failed to download PDF: {e}")
    return None

def extract_pdf_text(pdf_bytes):
    """Extracts text from PDF bytes."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Failed to extract PDF text: {e}")
        return ""

def clean_pdf_text(text):
    """Cleans up the extracted PDF text."""
    # Remove multiple spaces and newlines
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def classify_bse_event(text, title):
    """Detects and classifies BSE events."""
    combined_text = f"{title} {text}".lower()
    for event in EVENT_TYPES:
        if event.lower() in combined_text:
            return event
    return ""

def generate_keywords_from_ollama(text, title):
    """Extracts high quality keywords from the text using Ollama."""
    prompt = f"""
Extract the key financial entities and subjects from the following BSE announcement.
Focus only on:
1. Company Name(s) mentioned
2. Financial instruments (Equity Shares, NCDs, etc.)
3. The core subject of the notice

Do NOT include generic terms like 'Event Type', 'Sentiment', 'Impact Score', 'Unknown'.
Return ONLY a comma-separated list of the extracted keywords, nothing else.

Title: {title}
Content: {text[:3000]}
"""
    payload = {
        "model": "mistral:7b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 50,
            "num_ctx": 4096
        }
    }
    try:
        req = urllib.request.Request(
            OLLAMA_URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            raw_response = result.get("response", "")
            
            # Clean up the LLM response
            garbage = ["unknown", "event type", "sentiment", "impact score"]
            keywords = [k.strip() for k in raw_response.split(',') 
                        if k.strip() and k.strip().lower() not in garbage]
            return ", ".join(keywords)
    except Exception as e:
        logger.error(f"Failed to generate keywords from Ollama: {e}")
        return ""

def main():
    if len(sys.argv) < 3:
        logger.error("Error: Missing required arguments. Usage: python save_keywords.py <title> <keywords> [link]")
        sys.exit(1)

    title = sys.argv[1].lstrip("=")
    original_keywords = sys.argv[2]
    link = sys.argv[3] if len(sys.argv) > 3 else ""

    # Extract source_timestamp and system_timestamp (Phase 2 requirement)
    source_timestamp = sys.argv[4] if len(sys.argv) > 4 else ""
    if not source_timestamp:
        source_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    raw_text = title
    final_keywords = original_keywords
    event_type = ""

    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()

    # Check if article already processed
    cursor.execute("SELECT COUNT(*) FROM processed_articles WHERE article_id = ?", (link,))
    count = cursor.fetchone()[0]

    if count > 0:
        logger.info(f"Duplicate Found - Skipped: {link}")
        conn.close()
        sys.exit()

    # Intercept BSE PDF links
    if link and ('bseindia.com' in link.lower() and '.pdf' in link.lower()):
        logger.info("BSE PDF link detected, attempting full text extraction.")
        pdf_bytes = download_pdf(link)
        if pdf_bytes:
            pdf_text = extract_pdf_text(pdf_bytes)
            cleaned_text = clean_pdf_text(pdf_text)
            
            if cleaned_text:
                raw_text = cleaned_text
                event_type = classify_bse_event(cleaned_text, title)
                if event_type:
                    logger.info(f"Detected Event Type: {event_type}")
                
                new_keywords = generate_keywords_from_ollama(cleaned_text, title)
                if new_keywords:
                    final_keywords = new_keywords
                    logger.info(f"Generated new keywords from PDF: {final_keywords}")
                else:
                    logger.warning("Failed to generate new keywords, falling back to original.")
            else:
                logger.warning("Extracted PDF text was empty.")
        else:
            logger.warning("Could not download PDF.")
            event_type = classify_bse_event("", title)
    else:
        # Still try to classify based on title if it's not a PDF
        event_type = classify_bse_event("", title)

    # Clean the keywords to ensure no garbage slips through
    garbage_words = ["unknown", "event type", "sentiment", "impact score"]
    clean_kw_list = [k.strip() for k in final_keywords.split(',') 
                     if k.strip() and k.strip().lower() not in garbage_words]
    
    # Prepend event type to keywords if detected and not already in the list
    if event_type and not any(event_type.lower() == k.lower() for k in clean_kw_list):
        clean_kw_list.insert(0, event_type)
        
    final_keywords = ", ".join(clean_kw_list)

    # Convert keywords string into list for company/theme matching
    keyword_list = [k.lower() for k in clean_kw_list]

    # Company Matching
    related_companies = ""
    try:
        with open(MAPPING_FILE, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            matches = []
            for row in reader:
                keyword = row["keyword"].strip().lower()
                if keyword in keyword_list:
                    matches.append(row["companies"])
            matches = list(set(matches))
            related_companies = "|".join(matches)
    except Exception as e:
        logger.error(f"Error matching companies: {e}")

    # Theme Detection
    themes = []
    try:
        with open(THEME_FILE, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                keyword = row["keyword"].strip().lower()
                if keyword in keyword_list:
                    themes.append(row["theme"].strip())
        themes = sorted(list(set(themes)))
        detected_theme = "|".join(themes)
    except Exception as e:
        logger.error(f"Error matching themes: {e}")
        detected_theme = ""

    # Save to keywords table
    try:
        cursor.execute(
            """
            INSERT INTO keywords
            (title, raw_text, keywords, source, created_at, related_companies, theme, link, source_timestamp, system_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                raw_text,
                final_keywords,
                "RSS",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                related_companies,
                detected_theme,
                link,
                source_timestamp,
                system_timestamp
            )
        )

        cursor.execute(
            """
            INSERT INTO processed_articles
            (article_id, title, source_feed, processed_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                link,
                title,
                "RSS",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        conn.commit()
        logger.info("Saved Successfully to Database")
    except Exception as e:
        logger.error(f"Database error during insert: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()