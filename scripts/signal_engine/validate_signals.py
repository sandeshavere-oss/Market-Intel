import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime

# Resolve base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_MARKET_PATH = BASE_DIR / "database" / "market_intel.db"
DB_PRICE_PATH = BASE_DIR / "database" / "price_data.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "signal_engine.log"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Reconfigure stdout for UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def log_message(level, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} [{level}] {msg}"
    print(log_line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"Failed to write to log file: {e}")

def init_db():
    log_message("INFO", f"Ensuring signal_performance table exists in: {DB_MARKET_PATH}")
    conn = sqlite3.connect(DB_MARKET_PATH, timeout=30.0)
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
            FOREIGN KEY(signal_id) REFERENCES event_signals(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def get_trading_prices(symbol, start_date_str):
    if not DB_PRICE_PATH.exists():
        log_message("ERROR", f"Price database not found at: {DB_PRICE_PATH}")
        return []
        
    conn = sqlite3.connect(DB_PRICE_PATH)
    cursor = conn.cursor()
    
    # Fetch trading dates, open, close, and adj_close prices strictly AFTER the signal date
    try:
        cursor.execute("""
            SELECT date, open, close, adj_close 
            FROM price_history 
            WHERE symbol = ? AND date > ? 
            ORDER BY date ASC
        """, (symbol, start_date_str))
        rows = cursor.fetchall()
    except Exception as e:
        log_message("ERROR", f"Failed to query price history for {symbol}: {e}")
        rows = []
    finally:
        conn.close()
        
    return rows

def validate_signals():
    init_db()
    
    if not DB_MARKET_PATH.exists():
        log_message("ERROR", f"Market intelligence database not found at: {DB_MARKET_PATH}")
        return
        
    conn_market = sqlite3.connect(DB_MARKET_PATH, timeout=30.0)
    cur_market = conn_market.cursor()
    
    # 1. Clean up any historical mismatched rows in signal_performance
    # (Rows where signal_id < 4 do not match any actual event_signals.id in database)
    cur_market.execute("DELETE FROM signal_performance WHERE signal_id NOT IN (SELECT id FROM event_signals)")
    if cur_market.rowcount > 0:
        log_message("INFO", f"Removed {cur_market.rowcount} orphaned/mismatched rows from signal_performance.")
        conn_market.commit()
        
    # 2. Get all signals from event_signals
    cur_market.execute("SELECT id, company, signal_date FROM event_signals")
    signals = cur_market.fetchall()
    
    log_message("INFO", f"Retrieved {len(signals)} signals from event_signals.")
    
    validated_count = 0
    
    for sig in signals:
        sig_id, comp, sig_date = sig
        
        # Check if already validated and not PENDING
        cur_market.execute("""
            SELECT outcome FROM signal_performance 
            WHERE signal_id = ?
        """, (sig_id,))
        perf_row = cur_market.fetchone()
        
        if perf_row and perf_row[0] != 'PENDING':
            log_message("INFO", f"Signal ID {sig_id} ({comp} on {sig_date}) already validated. Skipping.")
            continue
            
        log_message("INFO", f"Validating Signal ID {sig_id} for {comp} (Signal Date: {sig_date})...")
        
        # Fetch price history strictly after the signal date
        prices = get_trading_prices(comp, sig_date)
        if not prices:
            log_message("WARNING", f"No price data found for {comp} after {sig_date}. Skipping.")
            continue
            
        # next trading day is index 0
        entry_date = prices[0][0]
        entry_price = prices[0][1] # next trading day's OPEN
        
        price_5d_later = None
        price_10d_later = None
        return_5d = None
        return_10d = None
        outcome = 'PENDING'
        
        # 5 trading days later (index 5 is 5 trading days after entry day index 0)
        if len(prices) > 5:
            price_5d_later = prices[5][3] if prices[5][3] is not None else prices[5][2] # ADJ_CLOSE or CLOSE
            return_5d = ((price_5d_later - entry_price) / entry_price) * 100
            
            # Determine outcome based on return_5d
            if return_5d > 2.0:
                outcome = 'WIN'
            elif return_5d < -2.0:
                outcome = 'LOSS'
            else:
                outcome = 'NEUTRAL'
                
        # 10 trading days later (index 10 is 10 trading days after entry day index 0)
        if len(prices) > 10:
            price_10d_later = prices[10][3] if prices[10][3] is not None else prices[10][2] # ADJ_CLOSE or CLOSE
            return_10d = ((price_10d_later - entry_price) / entry_price) * 100
            
        log_message("INFO", f"Calculated Returns for {comp}: Entry={entry_price:.2f} ({entry_date}), "
                            f"5D Close={f'{price_5d_later:.2f}' if price_5d_later else 'N/A'} (Ret={f'{return_5d:.2f}%' if return_5d is not None else 'N/A'}), "
                            f"10D Close={f'{price_10d_later:.2f}' if price_10d_later else 'N/A'} (Ret={f'{return_10d:.2f}%' if return_10d is not None else 'N/A'}). "
                            f"Outcome={outcome}")
                            
        # Insert or update signal_performance
        cur_market.execute("""
            INSERT OR REPLACE INTO signal_performance (
                signal_id, company, signal_date, price_at_signal, 
                price_5d_later, price_10d_later, return_5d, return_10d, outcome, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (sig_id, comp, sig_date, entry_price, price_5d_later, price_10d_later, return_5d, return_10d, outcome))
        validated_count += 1
        
    conn_market.commit()
    conn_market.close()
    log_message("INFO", f"Signal validation run completed. Processed {validated_count} records.")

if __name__ == "__main__":
    validate_signals()
