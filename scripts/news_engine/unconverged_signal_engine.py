import os
import sqlite3
import csv
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

# Reconfigure stdout to use UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_MARKET_PATH = BASE_DIR / "database" / "market_intel.db"
DB_PRICE_PATH = BASE_DIR / "database" / "price_data.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "unconverged_signal_engine.log"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_message(level, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} [{level}] {msg}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def init_db():
    log_message("INFO", f"Initializing unconverged_signals table in: {DB_MARKET_PATH}")
    conn = sqlite3.connect(DB_MARKET_PATH, timeout=60.0)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unconverged_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            signal_date TEXT,
            velocity REAL,
            today_mentions INTEGER,
            avg_mentions REAL,
            inferred_category TEXT,
            signal_strength TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company, signal_date)
        )
    """)
    conn.commit()
    conn.close()

def load_company_lookup():
    MASTER_FILE = BASE_DIR / "data" / "mappings" / "company_master.csv"
    lookup = {}
    if not MASTER_FILE.exists():
        log_message("WARNING", f"company_master.csv not found at {MASTER_FILE}")
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
                    
                lookup[symbol.lower()] = symbol
                lookup[name.lower()] = symbol
                
                aliases = [a.strip() for a in aliases_raw.split("|") if a.strip()]
                for alias in aliases:
                    lookup[alias.lower()] = symbol
    except Exception as e:
        log_message("ERROR", f"Failed to load company master: {e}")
    return lookup

def classify_article(title, theme, keywords_str):
    title = title.lower() if title else ""
    theme = theme.lower() if theme else ""
    kws = keywords_str.lower() if keywords_str else ""
    
    # 1. Corporate Event Driven
    event_kws = ["ipo", "listing", "quarterly results", "financial results", "earnings", "dividend", 
                 "board meeting", "merger", "acquisition", "takeover", "split", "bonus", "rights issue", "qip", "ofs", "quarterly", "board meet"]
    if any(k in title or k in kws for k in event_kws) or any(t in theme for t in ["capital markets", "financial performance"]):
        return "Corporate Event Driven"
        
    # 2. Regulatory Driven
    reg_kws = ["sebi", "rbi", "gst", "tax", "regulatory", "regulator", "guidelines", "compliance", "tariff", 
               "penalty", "fine", "supreme court", "license", "ed search", "enforcement directorate", "audit", "show cause"]
    if any(k in title or k in kws for k in reg_kws):
        return "Regulatory Driven"
        
    # 3. Macro Driven
    macro_kws = ["economy", "inflation", "gdp", "fed", "interest rate", "rate hike", "rate cut", "global market", 
                 "selloff", "jobs data", "rupee", "geopolitical", "war", "iran", "israel", "conflict", "ceasefire", 
                 "fii", "fpi", "outflows", "monsoon", "gift nifty", "nifty 50", "sensex"]
    if any(k in title or k in kws for k in macro_kws) or "macro economy" in theme:
        return "Macro Driven"
        
    # 4. Commodity Driven
    comm_kws = ["oil", "crude", "brent", "wti", "gold", "silver", "precious metals", "copper", "steel", 
                "aluminium", "zinc", "iron ore", "metals", "mining", "power", "coal", "gas", "lng", "commodity", "commodities"]
    if any(k in title or k in kws for k in comm_kws) or any(t in theme for t in ["commodities", "metals & mining", "energy"]):
        return "Commodity Driven"
        
    # 5. Theme Driven
    theme_kws = ["ai", "semiconductor", "defence", "space", "digital infrastructure", "ev", "telecom", "technology", "green energy"]
    if any(k in title or k in kws for k in theme_kws) or any(t in theme for t in ["ai", "semiconductor", "defence", "space economy", "digital infrastructure", "ev", "telecom", "technology", "green energy"]):
        return "Theme Driven"
        
    return "Company Specific News"  # Default fallback

def get_signal_category(company, date_str, lookup, cursor):
    # Query all matching articles for the company on the given date
    cursor.execute("""
        SELECT title, theme, keywords
        FROM keywords
        WHERE date(created_at) = ? AND processed = 1
    """, (date_str,))
    rows = cursor.fetchall()
    
    matching_articles = []
    for row in rows:
        title, theme, keywords_str = row
        mentioned = False
        title_lower = title.lower() if title else ""
        kws_lower = keywords_str.lower() if keywords_str else ""
        
        for alias, sym in lookup.items():
            if sym == company and len(alias) > 2:
                pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(pattern, title_lower) or alias in kws_lower:
                    mentioned = True
                    break
                    
        if mentioned:
            matching_articles.append((title, theme, keywords_str))
            
    # Vote
    votes = {
        "Corporate Event Driven": 0,
        "Regulatory Driven": 0,
        "Macro Driven": 0,
        "Commodity Driven": 0,
        "Theme Driven": 0,
        "Company Specific News": 0
    }
    
    for title, theme, keywords_str in matching_articles:
        cat = classify_article(title, theme, keywords_str)
        votes[cat] = votes.get(cat, 0) + 1
        
    if sum(votes.values()) > 0:
        return max(votes, key=votes.get)
    return "Company Specific News"

def generate_unconverged_signals(target_date_str=None):
    init_db()
    
    if not target_date_str:
        target_date_str = datetime.now().strftime("%Y-%m-%d")
        
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    
    # Calculate historical window
    start_date = target_date - timedelta(days=30)
    end_date = target_date - timedelta(days=1)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    log_message("INFO", f"Running Unconverged Breakout Engine for date: {target_date_str}")
    
    lookup = load_company_lookup()
    
    conn_market = sqlite3.connect(DB_MARKET_PATH, timeout=60.0)
    cur_market = conn_market.cursor()
    
    # Query today's mentions
    cur_market.execute("""
        SELECT company, mentions 
        FROM company_mentions 
        WHERE date = ?
    """, (target_date_str,))
    today_mentions_dict = {row[0]: row[1] for row in cur_market.fetchall()}
    
    # Query historical averages
    cur_market.execute("""
        SELECT company, AVG(mentions) 
        FROM company_mentions 
        WHERE date >= ? AND date <= ? 
        GROUP BY company
    """, (start_str, end_str))
    avg_mentions_dict = {row[0]: row[1] for row in cur_market.fetchall()}
    
    signals_count = 0
    
    for comp, today_count in today_mentions_dict.items():
        # Filter 1: Min Mentions >= 5
        if today_count < 5:
            continue
            
        avg_count = avg_mentions_dict.get(comp, 0.0)
        denom = avg_count if avg_count > 0 else 0.5
        velocity = today_count / denom
        
        # Filter 2: Min Velocity >= 3.0x
        if velocity >= 3.0:
            category = get_signal_category(comp, target_date_str, lookup, cur_market)
            
            # Filter 3: Exclude Regulatory Driven
            if category == "Regulatory Driven":
                log_message("INFO", f"Skipped Regulatory shock for {comp} (Velocity: {velocity:.2f}x, Mentions: {today_count})")
                continue
                
            # Filter 4: Conviction rules
            # High conviction if Theme Driven OR mentions > 10
            is_high_conviction = (category == "Theme Driven") or (today_count > 10)
            strength = "HIGH" if is_high_conviction else "MEDIUM"
            
            log_message("INFO", f"🌟 Unconverged Breakout Signal: {comp} | Category: {category} | Velocity: {velocity:.2f}x | Mentions: {today_count} | Conviction: {strength}")
            
            try:
                cur_market.execute("""
                    INSERT OR REPLACE INTO unconverged_signals (
                        company, signal_date, velocity, today_mentions, avg_mentions,
                        inferred_category, signal_strength
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (comp, target_date_str, velocity, today_count, avg_count, category, strength))
                signals_count += 1
            except Exception as e:
                log_message("ERROR", f"Failed to save unconverged signal for {comp}: {e}")
                
    conn_market.commit()
    conn_market.close()
    
    log_message("INFO", f"Unconverged Breakout Engine run completed. Generated {signals_count} signals.")

if __name__ == "__main__":
    target_dt = sys.argv[1] if len(sys.argv) > 1 else None
    generate_unconverged_signals(target_dt)
