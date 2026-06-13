import os
import sqlite3
import csv
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

# Reconfigure stdout to use UTF-8 (prevents crashes with emojis in terminal)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_MARKET_PATH = BASE_DIR / "database" / "market_intel.db"
DB_CORP_PATH = BASE_DIR / "database" / "corporate_events.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "signal_engine.log"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_message(level, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} [{level}] {msg}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def init_db():
    log_message("INFO", f"Initializing event_signals table in: {DB_MARKET_PATH}")
    conn = sqlite3.connect(DB_MARKET_PATH, timeout=60.0)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            signal_date TEXT,
            velocity REAL,
            today_mentions INTEGER,
            avg_mentions REAL,
            event_id INTEGER,
            event_type TEXT,
            event_date TEXT,
            event_description TEXT,
            signal_strength TEXT,
            signal_score REAL DEFAULT 0.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company, signal_date)
        )
    """)
    conn.commit()
    try:
        cursor.execute("ALTER TABLE event_signals ADD COLUMN signal_score REAL DEFAULT 0.0;")
        conn.commit()
        log_message("INFO", "Added signal_score column to event_signals table.")
    except sqlite3.OperationalError:
        pass
    conn.close()

def load_company_lookup():
    # Maps name/symbol/alias (lowercase) to standard symbol
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

def get_twitter_velocities(target_date_str, lookup):
    db_twitter_path = BASE_DIR / "database" / "twitter_intel.db"
    if not db_twitter_path.exists():
        log_message("WARNING", f"Twitter database not found at {db_twitter_path}")
        return {}
        
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    start_date = target_date - timedelta(days=30)
    end_date = target_date - timedelta(days=1)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(db_twitter_path, timeout=60.0)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT tweet_text, created_at 
            FROM tweets 
            WHERE date(created_at) >= ? AND date(created_at) <= ?
        """, (start_str, target_date_str))
        rows = cursor.fetchall()
    except Exception as e:
        log_message("ERROR", f"Failed to query tweets: {e}")
        rows = []
    finally:
        conn.close()
        
    daily_counts = {}
    for row in rows:
        text, created_at = row
        if not text or not created_at:
            continue
        try:
            date_part = created_at.split()[0]
            datetime.strptime(date_part, "%Y-%m-%d")
        except Exception:
            continue
            
        text_lower = text.lower()
        mentioned_symbols = set()
        
        for alias, symbol in lookup.items():
            if len(alias) > 2:
                pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(pattern, text_lower):
                    mentioned_symbols.add(symbol)
                    
        for symbol in mentioned_symbols:
            key = (symbol, date_part)
            daily_counts[key] = daily_counts.get(key, 0) + 1
            
    twitter_velocities = {}
    past_dates = []
    curr = start_date
    while curr <= end_date:
        past_dates.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
        
    all_symbols = set(lookup.values())
    for symbol in all_symbols:
        today_count = daily_counts.get((symbol, target_date_str), 0)
        past_counts = [daily_counts.get((symbol, d), 0) for d in past_dates]
        avg_30 = sum(past_counts) / len(past_counts) if past_counts else 0.0
        
        denom = max(avg_30, 0.5)
        velocity = today_count / denom
        
        twitter_velocities[symbol] = {
            "today_count": today_count,
            "avg_30": avg_30,
            "velocity": velocity
        }
        
    return twitter_velocities

def load_company_sectors():
    MASTER_FILE = BASE_DIR / "data" / "mappings" / "company_master.csv"
    sectors = {}
    if not MASTER_FILE.exists():
        log_message("WARNING", f"company_master.csv not found for sectors")
        return sectors
    try:
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row.get("symbol", "").strip()
                sector = row.get("sector", "").strip()
                if symbol:
                    sectors[symbol] = sector
    except Exception as e:
        log_message("ERROR", f"Failed to load company sectors: {e}")
    return sectors

def get_options_data_for_signal(symbol, date_str):
    """
    Queries options summary and nearest expiry chain data for a symbol on/before date_str.
    """
    db_price_path = BASE_DIR / "database" / "price_data.db"
    if not db_price_path.exists():
        return None
        
    conn = sqlite3.connect(db_price_path)
    cursor = conn.cursor()
    
    try:
        # 1. Fetch latest options summary on or before date_str
        cursor.execute("""
            SELECT pcr, underlying_price, snapshot_timestamp
            FROM options_summary
            WHERE symbol = ? AND date(snapshot_timestamp) <= ?
            ORDER BY snapshot_timestamp DESC
            LIMIT 1
        """, (symbol, date_str))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
            
        pcr, spot_price, snapshot_ts = row
        
        # 2. Get nearest expiry date for this snapshot
        cursor.execute("""
            SELECT MIN(expiry)
            FROM options_chain
            WHERE symbol = ? AND snapshot_timestamp = ?
        """, (symbol, snapshot_ts))
        expiry_row = cursor.fetchone()
        if not expiry_row or not expiry_row[0]:
            conn.close()
            return {"pcr": pcr, "implied_volatility": 0.0, "iv_percentile": None, "oi_skew": 0.0}
            
        nearest_expiry = expiry_row[0]
        
        # 3. Fetch ATM CE and PE rows (closest to spot price)
        cursor.execute("""
            SELECT implied_volatility, iv_percentile, change_in_oi, option_type
            FROM options_chain
            WHERE symbol = ? AND snapshot_timestamp = ? AND expiry = ?
            ORDER BY ABS(strike - ?) ASC
            LIMIT 2
        """, (symbol, snapshot_ts, nearest_expiry, spot_price))
        
        atm_rows = cursor.fetchall()
        
        iv_sum = 0.0
        iv_count = 0
        iv_percentile = None
        call_oi_change = 0
        put_oi_change = 0
        
        for iv, ivp, coi_chg, opt_type in atm_rows:
            if iv and iv > 0.0:
                iv_sum += iv
                iv_count += 1
                if ivp is not None:
                    iv_percentile = ivp
            if opt_type == "CE":
                call_oi_change += coi_chg or 0
            else:
                put_oi_change += coi_chg or 0
                
        avg_iv = iv_sum / iv_count if iv_count > 0 else 0.0
        
        # OI Skew
        denom = abs(call_oi_change) + abs(put_oi_change)
        oi_skew = (call_oi_change - put_oi_change) / denom if denom > 0 else 0.0
        
        conn.close()
        return {
            "pcr": pcr,
            "implied_volatility": avg_iv,
            "iv_percentile": iv_percentile,
            "oi_skew": oi_skew
        }
    except Exception as e:
        log_message("WARNING", f"Failed to query options data for {symbol}: {e}")
        if conn:
            conn.close()
        return None

def score_signal(comp, velocity, today_count, avg_count, has_event, event_type, target_date_str, cur_market, options_data=None):
    val_vel = min(max((velocity - 2.5) / 7.5, 0.0), 1.0) * 100.0
    val_count = min(max((today_count - 2) / 18.0, 0.0), 1.0) * 100.0
    
    sectors = load_company_sectors()
    sec = sectors.get(comp, "Unknown")
    
    theme_map = {
        "Financial Services": "Banking",
        "Energy": "Energy",
        "Utilities": "Energy",
        "Industrials": "Digital Infrastructure",
        "Information Technology": "Technology",
        "Consumer Discretionary": "Capital Markets",
        "Consumer Staples": "Capital Markets",
        "Healthcare": "Pharma",
        "Materials": "Metals & Mining",
        "Telecommunication": "Telecom"
    }
    theme = theme_map.get(sec, "Macro Economy")
    
    z_score = 0.0
    try:
        cur_market.execute("SELECT z_score FROM theme_velocity WHERE theme = ? AND date = ?", (theme, target_date_str))
        row = cur_market.fetchone()
        if row and row[0] is not None:
            z_score = row[0]
    except Exception as e:
        log_message("WARNING", f"Failed to fetch theme Z-score for {theme}: {e}")
        
    val_z = min(max(z_score / 4.0, 0.0), 1.0) * 100.0
    
    # Options-implied Event-Risk Discount for Corporate Events (Tier 1)
    val_event = 100.0 if has_event else 0.0
    val_options = 50.0  # Default neutral options factor score
    
    options_present = (options_data is not None and options_data.get("pcr") is not None)
    
    if options_present:
        pcr = options_data["pcr"]
        oi_skew = options_data.get("oi_skew", 0.0)
        iv_pct = options_data.get("iv_percentile")
        iv_abs = options_data.get("implied_volatility", 0.0)
        
        # Calculate Options Positioning Score (val_options)
        # PCR score: PCR < 0.65 is bullish (100 pts), PCR > 1.2 is bearish (0 pts), linear in between
        if pcr < 0.65:
            pcr_score = 100.0
        elif pcr > 1.2:
            pcr_score = 0.0
        else:
            pcr_score = 100.0 - ((pcr - 0.65) / (1.2 - 0.65)) * 100.0
            
        # Skew score: oi_skew > 0 confirms bullish trend (+50 pts max), < 0 contradicts (-50 pts max)
        skew_score = 50.0 + min(max(oi_skew * 50.0, -50.0), 50.0)
        
        val_options = 0.6 * pcr_score + 0.4 * skew_score
        
        # For Corporate Event signals (Tier 1), apply pre-event IV penalty to val_event
        if has_event:
            effective_iv_pct = iv_pct
            if effective_iv_pct is None and iv_abs > 0.0:
                # Absolute IV > 22% acts as elevated (85th percentile equivalent)
                effective_iv_pct = min(max((iv_abs / 30.0) * 100.0, 0.0), 100.0)
                
            if effective_iv_pct is not None and effective_iv_pct > 80.0:
                # Penalty ratio scales from 0% (at 80% percentile) to 100% (at 100% percentile)
                iv_penalty_ratio = min(max((effective_iv_pct - 80.0) / 20.0, 0.0), 1.0)
                val_event = 100.0 * (1.0 - iv_penalty_ratio)
                
    if sec in ["Defence", "Semiconductor", "Energy", "Green Energy", "Railways", "Financial Services", "Industrials"]:
        sector_strength = 100.0
    else:
        sector_strength = 60.0
        
    large_caps = {"RELIANCE", "TCS", "HDFCBANK", "SBIN", "LICI", "ONGC", "BHARTIARTL", "HAL", "BEL", "INFY", "WIPRO", "HCLTECH", "ICICIBANK", "AXISBANK"}
    if comp in large_caps:
        mcap_score = 100.0
    elif sec in ["Healthcare", "Pharma", "Materials"]:
        mcap_score = 75.0
    else:
        mcap_score = 50.0
        
    hist_score = 70.0
    
    if options_present:
        # Rebalanced weights (Options 10%, Velocity 20%, Count 10%)
        score = (
            0.20 * val_vel +
            0.10 * val_count +
            0.20 * val_z +
            0.15 * val_event +
            0.10 * sector_strength +
            0.10 * val_options +
            0.05 * mcap_score +
            0.10 * hist_score
        )
    else:
        # Original weights (No options data)
        score = (
            0.25 * val_vel +
            0.15 * val_count +
            0.20 * val_z +
            0.15 * val_event +
            0.10 * sector_strength +
            0.05 * mcap_score +
            0.10 * hist_score
        )
        
    return round(score, 2)

def generate_signals(target_date_str=None):
    init_db()
    
    if not target_date_str:
        # Default to today
        target_date_str = datetime.now().strftime("%Y-%m-%d")
        
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    
    # Load company and Twitter lookup statistics
    lookup = load_company_lookup()
    twitter_stats = get_twitter_velocities(target_date_str, lookup)
    
    # Calculate date ranges for velocity
    # 30 days prior to target date
    start_date = target_date - timedelta(days=30)
    end_date = target_date - timedelta(days=1)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    log_message("INFO", f"Calculating mention velocity for date: {target_date_str}")
    log_message("INFO", f"30-day average window: {start_str} to {end_str}")
    
    conn_market = sqlite3.connect(DB_MARKET_PATH, timeout=60.0)
    cur_market = conn_market.cursor()
    
    # 1. Fetch mention statistics for all companies on target_date and historical window
    # Let's get today's mentions
    cur_market.execute("""
        SELECT company, mentions 
        FROM company_mentions 
        WHERE date = ?
    """, (target_date_str,))
    today_mentions_dict = {row[0]: row[1] for row in cur_market.fetchall()}
    
    # Let's get historical averages
    cur_market.execute("""
        SELECT company, AVG(mentions) 
        FROM company_mentions 
        WHERE date >= ? AND date <= ? 
        GROUP BY company
    """, (start_str, end_str))
    avg_mentions_dict = {row[0]: row[1] for row in cur_market.fetchall()}
    
    # 2. Find upcoming corporate events (next 7 days) from corporate_events.db
    # Upcoming window: from target_date to target_date + 7 days
    up_end_date = target_date + timedelta(days=7)
    up_end_str = up_end_date.strftime("%Y-%m-%d")
    
    conn_corp = sqlite3.connect(DB_CORP_PATH, timeout=60.0)
    cur_corp = conn_corp.cursor()
    
    log_message("INFO", f"Querying corporate events from {target_date_str} to {up_end_str}")
    
    # We query the unified corporate_events table
    # Standard format for dates: YYYY-MM-DD or text representation.
    # To handle date comparison robustly in SQLite for text dates, we'll fetch all future events and filter in Python
    cur_corp.execute("""
        SELECT id, company_symbol, event_date, event_type, description 
        FROM corporate_events
        UNION ALL
        SELECT id, company_symbol, meeting_date AS event_date, 'board_meeting' AS event_type, purpose AS description 
        FROM board_meetings
        UNION ALL
        SELECT id, company_symbol, date(created_at) AS event_date, 'financial_results' AS event_type, outcome_summary AS description 
        FROM financial_results
    """)
    raw_events = cur_corp.fetchall()
    
    # Deduplicate events in Python based on (company_symbol, event_date_standardized, event_type)
    seen_events = set()
    all_events = []
    for ev in raw_events:
        ev_id, sym, ev_date_str, ev_type, desc = ev
        if not sym or not ev_date_str or not ev_type:
            continue
        
        parsed_ev_date = None
        for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
            try:
                parsed_ev_date = datetime.strptime(ev_date_str.strip(), fmt)
                break
            except Exception:
                continue
        std_date = parsed_ev_date.strftime("%Y-%m-%d") if parsed_ev_date else ev_date_str.strip()
        
        key = (sym.strip().upper(), std_date, ev_type.strip().lower())
        if key not in seen_events:
            seen_events.add(key)
            all_events.append(ev)
    
    # Filter upcoming events in Python
    upcoming_events = []
    for ev in all_events:
        ev_id, sym, ev_date_str, ev_type, desc = ev
        # Try parsing date string
        # Some event_date might be like 'June 15, 2026' or '2026-06-15'
        parsed_ev_date = None
        for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
            try:
                parsed_ev_date = datetime.strptime(ev_date_str.strip(), fmt)
                break
            except Exception:
                continue
                
        if parsed_ev_date:
            # Check if event date is between target_date and target_date + 7 days
            if target_date <= parsed_ev_date <= up_end_date:
                upcoming_events.append({
                    "id": ev_id,
                    "symbol": sym,
                    "date": parsed_ev_date.strftime("%Y-%m-%d"),
                    "type": ev_type,
                    "description": desc,
                    "days_away": (parsed_ev_date - target_date).days
                })
        else:
            # Fallback check if date string contains month/year matching next 7 days
            # Just default include if company symbol matches and it contains a date in focus
            continue
            
    log_message("INFO", f"Found {len(upcoming_events)} upcoming corporate events in next 7 days.")
    
    # Organize upcoming events by company symbol
    company_events = {}
    for ev in upcoming_events:
        sym = ev["symbol"]
        if sym not in company_events:
            company_events[sym] = []
        company_events[sym].append(ev)
        
    # 3. Calculate velocity and flag spikes
    signals_count = 0
    
    for comp, today_count in today_mentions_dict.items():
        # Minimum count to filter out noise
        if today_count < 2:
            continue
            
        avg_count = avg_mentions_dict.get(comp, 0.0)
        
        # Avoid division by zero
        denom = avg_count if avg_count > 0 else 0.5
        velocity = today_count / denom
        
        # Spike check (Velocity > 2.5x)
        if velocity > 2.5:
            log_message("INFO", f"🔥 Velocity spike detected for {comp}: {velocity:.2f}x (Today: {today_count}, 30d Avg: {avg_count:.2f})")
            
            # Get Twitter velocity multiplier for the company
            comp_twitter = twitter_stats.get(comp, {"today_count": 0, "avg_30": 0.0, "velocity": 0.0})
            tweet_vol_mult = comp_twitter["velocity"]
            
            # Check if company has an upcoming event
            events = company_events.get(comp, [])
            for ev in events:
                # Conviction Rating: HIGH if event is <= 4 days away OR tweet velocity is >= 3.0x (3x volume)
                strength = "HIGH" if (ev["days_away"] <= 4 or tweet_vol_mult >= 3.0) else "MEDIUM"
                
                log_message("INFO", f"🚨 Signal Convergence for {comp}: Velocity Spike ({velocity:.2f}x) + Upcoming {ev['type']} ({ev['days_away']} days away) + Twitter Velocity: {tweet_vol_mult:.2f}x. Conviction: {strength}")
                
                try:
                    options_data = get_options_data_for_signal(comp, target_date_str)
                    score = score_signal(comp, velocity, today_count, avg_count, True, ev["type"], target_date_str, cur_market, options_data=options_data)
                    cur_market.execute("""
                        INSERT OR REPLACE INTO event_signals (
                            company, signal_date, velocity, today_mentions, avg_mentions,
                            event_id, event_type, event_date, event_description, signal_strength, signal_score
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        comp, target_date_str, velocity, today_count, avg_count,
                        ev["id"], ev["type"], ev["date"], ev["description"], strength, score
                    ))
                    signals_count += 1
                    log_message("INFO", f"Saved Convergence Signal for {comp} with Score: {score}")
                except Exception as e:
                    log_message("ERROR", f"Failed to save signal for {comp}: {e}")
                    
    conn_market.commit()
    conn_market.close()
    conn_corp.close()
    
    log_message("INFO", f"Signal engine run completed. Generated {signals_count} new signals.")

if __name__ == "__main__":
    import sys
    target_dt = sys.argv[1] if len(sys.argv) > 1 else None
    generate_signals(target_dt)
