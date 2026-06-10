import os
import sqlite3
import csv
import logging
import requests
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# Resolve base paths dynamically
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "corporate_events.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "corporate_engine.log"
MASTER_FILE = BASE_DIR / "data" / "mappings" / "company_master.csv"

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
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)

def init_db():
    logging.info(f"Initializing database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Existing tables (keep for backwards compatibility)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS board_meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_symbol TEXT,
            meeting_date TEXT,
            purpose TEXT,
            source TEXT,
            guid TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_symbol TEXT,
            quarter TEXT,
            financial_year TEXT,
            revenue REAL,
            net_profit REAL,
            outcome_summary TEXT,
            guid TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Unified corporate_events table for Phase 3
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS corporate_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_symbol TEXT,
            event_date TEXT,
            event_type TEXT,
            description TEXT,
            source TEXT,
            guid TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def load_company_master() -> list:
    companies = []
    if not MASTER_FILE.exists():
        logging.warning(f"Company master file not found at {MASTER_FILE}")
        return companies
        
    try:
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("company_name", "").strip()
                symbol = row.get("symbol", "").strip()
                aliases_raw = row.get("aliases", "").strip()
                aliases = [a.strip().lower() for a in aliases_raw.split("|") if a.strip()]
                
                companies.append({
                    "name": name,
                    "symbol": symbol,
                    "aliases": aliases + [name.lower(), symbol.lower()]
                })
    except Exception as e:
        logging.error(f"Error loading company master: {e}")
        
    return companies

def match_company_symbol(title: str, company_list: list) -> str:
    title_lower = title.lower()
    for comp in company_list:
        for alias in comp["aliases"]:
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, title_lower):
                return comp["symbol"]
    return "Unknown"

def query_ollama(title: str) -> dict:
    url = "http://localhost:11434/api/generate"
    prompt = f"""Analyze this stock exchange notice title and extract corporate financial event data in JSON.
Notice: {title}

Return EXACTLY a JSON block with keys:
{{
  "event_type": "board_meeting" | "financial_results" | "dividend" | "bonus" | "split" | "buyback" | "qip" | "order_win" | "m&a" | "other",
  "company_name": "extracted company name or null",
  "event_date": "YYYY-MM-DD" or null,
  "purpose": "short description of purpose or null",
  "quarter": "Q1" | "Q2" | "Q3" | "Q4" or null,
  "financial_year": "FY26" or null,
  "revenue": float or null,
  "net_profit": float or null,
  "outcome_summary": "short summary of event outcome or null"
}}

Rules:
- Output ONLY valid JSON, no markdown, no other text outside the JSON block.
- Do not guess financial numbers (revenue/profit) if not in the title. Set to null.
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
        response = requests.post(url, json=payload, timeout=240)
        if response.status_code == 200:
            raw_text = response.json().get("response", "").strip()
            raw_text = re.sub(r"^```json\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)
            return json.loads(raw_text)
    except Exception as e:
        logging.error(f"Ollama API call failed: {e}")
        
    return None

def fallback_regex_parser(title: str, pub_date_str: str) -> dict:
    title_lower = title.lower()
    event_type = "other"
    
    # Try classifying using regex patterns
    if any(k in title_lower for k in ["board meeting", "meeting of board", "meeting of the board"]):
        event_type = "board_meeting"
    elif any(k in title_lower for k in ["financial results", "quarterly results", "audited results", "un-audited"]):
        event_type = "financial_results"
    elif "dividend" in title_lower:
        event_type = "dividend"
    elif "bonus" in title_lower:
        event_type = "bonus"
    elif "split" in title_lower:
        event_type = "split"
    elif "buyback" in title_lower:
        event_type = "buyback"
    elif "qip" in title_lower:
        event_type = "qip"
    elif any(k in title_lower for k in ["order win", "award of contract", "secures order"]):
        event_type = "order_win"
    elif any(k in title_lower for k in ["merger", "acquisition", "m&a", "amalgamation"]):
        event_type = "m&a"
        
    data = {
        "event_type": event_type,
        "event_date": None,
        "purpose": title,
        "quarter": None,
        "financial_year": None,
        "revenue": None,
        "net_profit": None,
        "outcome_summary": title
    }
    
    # Try extracting date like "June 15, 2026" or YYYY-MM-DD
    date_match = re.search(r"\b([a-zA-Z]+ \d{1,2},? \d{4})\b", title)
    if date_match:
        data["event_date"] = date_match.group(1)
    else:
        # Fallback to publication date
        data["event_date"] = pub_date_str
            
    if event_type == "financial_results":
        q_match = re.search(r"\b(q[1-4])\b", title_lower)
        if q_match:
            data["quarter"] = q_match.group(1).upper()
        fy_match = re.search(r"\b(fy\d{2})\b", title_lower)
        if fy_match:
            data["financial_year"] = fy_match.group(1).upper()
        else:
            year_match = re.search(r"\b(20\d{2})\b", title_lower)
            if year_match:
                data["financial_year"] = f"FY{year_match.group(1)[2:]}"
                
    return data

def process_notices():
    logging.info("Starting BSE notices ingestion...")
    feed_url = "https://www.bseindia.com/data/xml/notices.xml"
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(feed_url, headers=headers, timeout=30)
        if response.status_code != 200:
            logging.error(f"Failed to fetch BSE feed. HTTP Status: {response.status_code}")
            return
    except Exception as e:
        logging.error(f"Request error fetching BSE feed: {e}")
        return
        
    try:
        xml_data = response.content.decode("utf-8-sig")
        root = ET.fromstring(xml_data.encode("utf-8"))
    except Exception as e:
        logging.error(f"XML parsing error: {e}")
        return
        
    company_list = load_company_master()
    logging.info(f"Loaded {len(company_list)} companies from master.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    items = root.findall(".//item")
    logging.info(f"Found {len(items)} items in RSS feed.")
    
    inserted_meetings = 0
    inserted_results = 0
    inserted_unified = 0
    
    for item in items:
        title = item.find("title").text if item.find("title") is not None else ""
        link = item.find("link").text if item.find("link") is not None else ""
        pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
        guid = item.find("guid").text if item.find("guid") is not None else link
        
        if not title:
            continue
            
        title_lower = title.lower()
        
        # Pre-filter: include dividends, split, buyback, order wins, M&A
        is_relevant = any(k in title_lower for k in [
            "board meeting", "meeting of board", "meeting of the board", "meeting to consider",
            "financial results", "quarterly results", "audited results", "un-audited",
            "dividend", "bonus", "split", "buyback", "qip", "order win", "award of contract",
            "merger", "acquisition", "m&a"
        ])
        
        if not is_relevant:
            continue
            
        # Check uniqueness in corporate_events table
        cursor.execute("SELECT 1 FROM corporate_events WHERE guid = ?", (guid,))
        if cursor.fetchone():
            continue
            
        logging.info(f"Processing notice: '{title}'")
        symbol = match_company_symbol(title, company_list)
        
        # Call Ollama for structuring
        event_data = query_ollama(title)
        if not event_data:
            event_data = fallback_regex_parser(title, pub_date)
            
        event_type = event_data.get("event_type", "other")
        
        # Map values to unified corporate_events schema
        event_date = event_data.get("event_date") or event_data.get("meeting_date") or pub_date
        purpose = event_data.get("purpose") or event_data.get("outcome_summary") or title
        
        # Store in unified corporate_events table
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO corporate_events (company_symbol, event_date, event_type, description, source, guid)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (symbol, event_date, event_type, purpose, "BSE Notices", guid)
            )
            inserted_unified += 1
        except Exception as e:
            logging.error(f"Error saving unified corporate event: {e}")
            
        # Backwards compatibility tables
        if event_type == "board_meeting":
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO board_meetings (company_symbol, meeting_date, purpose, source, guid)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (symbol, event_date, purpose, "BSE Notices", guid)
                )
                inserted_meetings += 1
            except Exception as e:
                logging.error(f"Error saving board meeting: {e}")
                
        elif event_type == "financial_results":
            quarter = event_data.get("quarter")
            fy = event_data.get("financial_year")
            revenue = event_data.get("revenue")
            profit = event_data.get("net_profit")
            summary = event_data.get("outcome_summary") or title
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO financial_results (company_symbol, quarter, financial_year, revenue, net_profit, outcome_summary, guid)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (symbol, quarter, fy, revenue, profit, summary, guid)
                )
                inserted_results += 1
            except Exception as e:
                logging.error(f"Error saving financial results: {e}")
                
    conn.commit()
    conn.close()
    
    logging.info(f"Ingestion completed. Saved unified: {inserted_unified}, meetings: {inserted_meetings}, results: {inserted_results}")

if __name__ == "__main__":
    init_db()
    try:
        process_notices()
    except Exception as ex:
        logging.critical(f"Unhandled exception in corporate engine: {ex}", exc_info=True)
