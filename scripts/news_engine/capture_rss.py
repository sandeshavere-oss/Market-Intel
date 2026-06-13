import sqlite3
import sys
import logging
import re
import csv
import urllib.request
import urllib.error
import io
from datetime import datetime
from pathlib import Path
from pypdf import PdfReader

# Setup Logging via shared module
sys.path.append(str(Path(__file__).resolve().parent))
from logger_setup import get_logger
logger = get_logger("capture_rss.py")

# Resolve Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "market_intel.db"
MASTER_FILE = BASE_DIR / "data" / "mappings" / "company_master.csv"
COMPANY_MAP_FILE = BASE_DIR / "data" / "mappings" / "company_mapping.csv"
THEME_MAP_FILE = BASE_DIR / "data" / "mappings" / "theme_mapping.csv"

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
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def classify_bse_event(text, title):
    """Detects and classifies BSE events deterministically."""
    combined_text = f"{title} {text}".lower()
    for event in EVENT_TYPES:
        if event.lower() in combined_text:
            return event
    return ""

def deterministic_match(text):
    """
    Perform highly optimized deterministic matching for companies and themes.
    Matches names, symbols, and aliases using word-boundary regexes.
    """
    matched_companies = set()
    matched_themes = set()

    # 1. Match using company_master.csv
    if MASTER_FILE.exists():
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("company_name", "").strip()
                    symbol = row.get("symbol", "").strip()
                    aliases_raw = row.get("aliases", "").strip()
                    
                    terms = [name, symbol]
                    if aliases_raw:
                        terms.extend([a.strip() for a in aliases_raw.split("|") if a.strip()])
                    
                    # Clean and compile regex pattern
                    terms = [t for t in terms if t]
                    if terms:
                        pattern = r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\b"
                        if re.search(pattern, text, re.IGNORECASE):
                            matched_companies.add(name)
        except Exception as e:
            logger.error(f"Error reading company master: {e}")

    # 2. Match using company_mapping.csv
    if COMPANY_MAP_FILE.exists():
        try:
            with open(COMPANY_MAP_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    keyword = row.get("keyword", "").strip()
                    companies_raw = row.get("companies", "").strip()
                    if keyword and companies_raw:
                        pattern = r"\b" + re.escape(keyword) + r"\b"
                        if re.search(pattern, text, re.IGNORECASE):
                            for c in companies_raw.split("|"):
                                if c.strip():
                                    matched_companies.add(c.strip())
        except Exception as e:
            logger.error(f"Error reading company mappings: {e}")

    # 3. Match using theme_mapping.csv
    if THEME_MAP_FILE.exists():
        try:
            with open(THEME_MAP_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    keyword = row.get("keyword", "").strip()
                    theme = row.get("theme", "").strip()
                    if keyword and theme:
                        pattern = r"\b" + re.escape(keyword) + r"\b"
                        if re.search(pattern, text, re.IGNORECASE):
                            matched_themes.add(theme)
        except Exception as e:
            logger.error(f"Error reading theme mappings: {e}")

    return sorted(list(matched_companies)), sorted(list(matched_themes))

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
        title = base64_payload.get("title", "").lstrip("=")
        content = base64_payload.get("content", "")
        link = base64_payload.get("link", "")
        source_feed = base64_payload.get("source_feed", "RSS")
        source_timestamp = base64_payload.get("source_timestamp", "")
    else:
        if len(sys.argv) < 3:
            logger.error("Usage: python capture_rss.py <title> <content> [link] [source_feed]")
            sys.exit(1)

        title = sys.argv[1].lstrip("=")
        content = sys.argv[2]
        link = sys.argv[3] if len(sys.argv) > 3 else ""
        source_feed = sys.argv[4] if len(sys.argv) > 4 else "RSS"
        source_timestamp = sys.argv[5] if len(sys.argv) > 5 else ""

    # Extract source_timestamp and system_timestamp (Phase 2 requirement)
    if not source_timestamp:
        source_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    raw_text = content if content else title
    event_type = ""

    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()

    # Duplicate Check
    cursor.execute("SELECT COUNT(*) FROM processed_articles WHERE article_id = ?", (link,))
    if cursor.fetchone()[0] > 0:
        logger.warning(f"Duplicate Found - Skipped: {link}")
        conn.close()
        return 0

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
            else:
                logger.warning("Extracted PDF text was empty.")
        else:
            logger.warning("Could not download PDF.")
            event_type = classify_bse_event("", title)
    else:
        event_type = classify_bse_event("", title)

    # Run Deterministic Match
    combined_matching_text = f"{title} {raw_text}"
    matched_cos, matched_themes = deterministic_match(combined_matching_text)

    related_companies = "|".join(matched_cos)
    detected_themes = "|".join(matched_themes)

    # Default keywords to event type if found, or simple comma list of entities
    keywords_list = []
    if event_type:
        keywords_list.append(event_type)
    keywords_list.extend(matched_cos)
    keywords_list.extend(matched_themes)
    keywords_str = ", ".join(list(set(keywords_list)))

    # Save to keywords database table as processed = 0
    try:
        cursor.execute(
            """
            INSERT INTO keywords
            (title, raw_text, keywords, source, created_at, related_companies, theme, link, 
             processed, company_match_count, theme_match_count, source_timestamp, system_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (
                title,
                raw_text,
                keywords_str,
                source_feed,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                related_companies,
                detected_themes,
                link,
                len(matched_cos),
                len(matched_themes),
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
                source_feed,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        conn.commit()
        logger.info(f"Successfully captured and stored article: '{title}' (Companies: {len(matched_cos)}, Themes: {len(matched_themes)})")
        return 1
    except Exception as e:
        logger.error(f"Database error during insert: {e}")
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
