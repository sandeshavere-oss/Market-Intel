import os
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_MARKET_PATH = BASE_DIR / "database" / "market_intel.db"
DB_PRICE_PATH = BASE_DIR / "database" / "price_data.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "performance_tracker.log"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Reconfigure stdout to use UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def log_message(level, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} [{level}] {msg}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def init_db():
    log_message("INFO", f"Initializing signal_performance table in: {DB_MARKET_PATH}")
    conn = sqlite3.connect(DB_MARKET_PATH, timeout=60.0)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signal_performance (
            signal_id INTEGER PRIMARY KEY,
            company TEXT,
            signal_date TEXT,
            price_at_signal REAL,
            price_5d_later REAL,
            price_10d_later REAL,
            return_5d REAL,
            return_10d REAL,
            outcome TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(signal_id) REFERENCES event_signals(id)
        )
    """)
    conn.commit()
    conn.close()

def get_trading_prices(company, start_date_str):
    # Fetch all trading dates and close prices for this company after start_date_str
    if not DB_PRICE_PATH.exists():
        return []
        
    conn = sqlite3.connect(DB_PRICE_PATH, timeout=60.0)
    cursor = conn.cursor()
    
    # Check if price_history table exists (Step 2 requires NIFTY/F&O price history)
    # Fallback to daily_prices if price_history doesn't exist
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_history'")
        has_history = cursor.fetchone() is not None
        
        if has_history:
            cursor.execute("""
                SELECT trade_date as date, close 
                FROM price_history 
                WHERE symbol = ? AND trade_date >= ? 
                ORDER BY trade_date ASC
            """, (company, start_date_str))
        else:
            cursor.execute("""
                SELECT date, close 
                FROM daily_prices 
                WHERE symbol = ? AND date >= ? 
                ORDER BY date ASC
            """, (company, start_date_str))
            
        rows = cursor.fetchall()
    except Exception as e:
        log_message("ERROR", f"Failed to query price database: {e}")
        rows = []
        
    conn.close()
    return rows

def get_nifty_price_on_date(date_str):
    if not DB_PRICE_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PRICE_PATH, timeout=60.0)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT close FROM price_history WHERE symbol = 'NIFTY50' AND trade_date = ?", (date_str,))
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute("SELECT close FROM daily_prices WHERE symbol = 'NIFTY50' AND date = ?", (date_str,))
        row = cursor.fetchone()
        if row:
            return row[0]
    except Exception as e:
        log_message("ERROR", f"Failed to query Nifty price on {date_str}: {e}")
    finally:
        conn.close()
    return None

def track_performance():
    init_db()
    
    conn_market = sqlite3.connect(DB_MARKET_PATH, timeout=60.0)
    cur_market = conn_market.cursor()
    
    # Query all generated signals
    cur_market.execute("""
        SELECT id, company, signal_date 
        FROM event_signals
    """)
    signals = cur_market.fetchall()
    log_message("INFO", f"Found {len(signals)} signals to track performance.")
    
    tracker_count = 0
    
    for sig in signals:
        sig_id, comp, sig_date = sig
        
        # Get price history starting from signal date
        prices = get_trading_prices(comp, sig_date)
        if not prices:
            log_message("WARNING", f"No price data found for {comp} starting from {sig_date}. Skipping.")
            continue
            
        # prices is a list of (date, close_price) sorted by date
        # price_at_signal is the first available trading day price (index 0)
        date_at_signal = prices[0][0]
        price_at_signal = prices[0][1]
        
        price_5d_later = None
        price_10d_later = None
        return_5d = None
        return_10d = None
        outcome = "PENDING"
        
        # Check if 5 trading days have passed (need at least 6 trading days: index 0 to 5)
        if len(prices) > 5:
            date_5d = prices[5][0]
            price_5d_later = prices[5][1]
            return_5d = ((price_5d_later - price_at_signal) / price_at_signal) * 100
            
            # Fetch Nifty prices for outperformance comparison
            nifty_at_signal = get_nifty_price_on_date(date_at_signal)
            nifty_5d = get_nifty_price_on_date(date_5d)
            
            if nifty_at_signal and nifty_5d:
                nifty_ret_5d = ((nifty_5d - nifty_at_signal) / nifty_at_signal) * 100
                outperformance_5d = return_5d - nifty_ret_5d
                
                if outperformance_5d > 0.0:
                    outcome = "WIN"
                elif outperformance_5d < 0.0:
                    outcome = "LOSS"
                else:
                    outcome = "NEUTRAL"
                log_message("INFO", f"Signal {sig_id} ({comp} on {sig_date}): Stock return: {return_5d:.2f}%, Nifty return: {nifty_ret_5d:.2f}%, Outperformance: {outperformance_5d:+.2f}%. Outcome: {outcome}")
            else:
                log_message("WARNING", f"Nifty price data missing for dates {date_at_signal} or {date_5d}. Keeping PENDING.")
            
        # Check if 10 trading days have passed (need at least 11 trading days: index 0 to 10)
        if len(prices) > 10:
            price_10d_later = prices[10][1]
            return_10d = ((price_10d_later - price_at_signal) / price_at_signal) * 100
                
        try:
            cur_market.execute("""
                INSERT OR REPLACE INTO signal_performance (
                    signal_id, company, signal_date, price_at_signal,
                    price_5d_later, price_10d_later, return_5d, return_10d, outcome, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                sig_id, comp, sig_date, price_at_signal,
                price_5d_later, price_10d_later, return_5d, return_10d, outcome
            ))
            tracker_count += 1
        except Exception as e:
            log_message("ERROR", f"Failed to save performance for signal {sig_id}: {e}")
            
    conn_market.commit()
    conn_market.close()
    log_message("INFO", f"Performance tracking run completed. Updated {tracker_count} signal performance records.")

if __name__ == "__main__":
    track_performance()
