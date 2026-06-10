import os
import sqlite3
import csv
import sys
import re
from pathlib import Path
from datetime import datetime

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "DATABASE" / "market_intel.db"
MASTER_FILE = BASE_DIR / "MAPPINGS" / "company_master.csv"
LOG_DIR = BASE_DIR / "LOGS"
LOG_FILE = LOG_DIR / "mention_engine.log"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_message(level, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} [{level}] {msg}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def init_db():
    log_message("INFO", f"Initializing mention table in: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_mentions (
            company TEXT,
            date TEXT,
            mentions INTEGER,
            PRIMARY KEY (company, date)
        )
    """)
    conn.commit()
    conn.close()

def load_company_lookup():
    # Maps name/symbol/alias (lowercase) to standard symbol
    lookup = {}
    if not MASTER_FILE.exists():
        log_message("ERROR", f"company_master.csv not found at {MASTER_FILE}")
        return lookup
        
    try:
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row.get("symbol", "").strip()
                name = row.get("company_name", "").strip()
                aliases_raw = row.get("aliases", "").strip()
                
                if not symbol:
                    continue
                    
                # Map symbol and name
                lookup[symbol.lower()] = symbol
                lookup[name.lower()] = symbol
                
                # Map aliases
                aliases = [a.strip() for a in aliases_raw.split("|") if a.strip()]
                for alias in aliases:
                    lookup[alias.lower()] = symbol
    except Exception as e:
        log_message("ERROR", f"Failed to load company master: {e}")
        
    return lookup

def calculate_mentions():
    init_db()
    lookup = load_company_lookup()
    if not lookup:
        log_message("ERROR", "No company lookup mappings found. Exiting.")
        return

    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    cursor = conn.cursor()

    # Query all keywords articles
    log_message("INFO", "Querying keywords table for company mentions...")
    cursor.execute("""
        SELECT related_companies, created_at, title, keywords
        FROM keywords
        WHERE processed = 1
    """)
    rows = cursor.fetchall()
    log_message("INFO", f"Found {len(rows)} processed articles.")

    # Dictionary to aggregate: {(symbol, date): count}
    mention_agg = {}

    for row in rows:
        related_cos_str, created_at, title, keywords = row
        if not created_at:
            continue
            
        # Parse date YYYY-MM-DD
        try:
            date_part = created_at.split()[0]
            # Verify date format
            datetime.strptime(date_part, "%Y-%m-%d")
        except Exception:
            # Fallback/skip if invalid date
            continue

        mentioned_symbols_in_article = set()

        # 1. Parse related_companies column
        if related_cos_str:
            parts = [p.strip() for p in related_cos_str.split("|") if p.strip()]
            for part in parts:
                symbol = lookup.get(part.lower())
                if symbol:
                    mentioned_symbols_in_article.add(symbol)

        # 2. Extract from title/keywords for redundancy if related_companies is empty
        # This makes the counter robust to missing related_companies
        title_lower = title.lower() if title else ""
        kws_lower = keywords.lower() if keywords else ""
        
        for alias, symbol in lookup.items():
            # Use word boundary search for aliases to avoid substring issues
            if len(alias) > 2: # Ignore very short aliases to avoid noise
                pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(pattern, title_lower) or alias in kws_lower:
                    mentioned_symbols_in_article.add(symbol)

        # Increment counts
        for symbol in mentioned_symbols_in_article:
            key = (symbol, date_part)
            mention_agg[key] = mention_agg.get(key, 0) + 1

    # Save to database
    log_message("INFO", f"Inserting/updating {len(mention_agg)} mention records...")
    
    rows_to_insert = [(sym, dt, count) for (sym, dt), count in mention_agg.items()]
    
    # We clear the existing mentions table before reload to prevent stale data
    # (Since this is a full reload of the keywords table, which is very fast)
    cursor.execute("DELETE FROM company_mentions")
    
    cursor.executemany("""
        INSERT OR REPLACE INTO company_mentions (company, date, mentions)
        VALUES (?, ?, ?)
    """, rows_to_insert)

    conn.commit()
    conn.close()
    log_message("INFO", "Company mention counts completed successfully!")

if __name__ == "__main__":
    calculate_mentions()
