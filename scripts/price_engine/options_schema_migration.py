import os
import sqlite3
import sys
from pathlib import Path

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "price_data.db"

def init_options_db():
    print(f"Initializing options database tables in: {DB_PATH}")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable WAL mode for concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Create options_chain table
    # Primary key is a composite of (symbol, expiry, strike, option_type, snapshot_timestamp)
    # to allow historical snapshots to accumulate.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS options_chain (
            symbol TEXT,
            expiry TEXT,                  -- YYYY-MM-DD
            strike REAL,
            option_type TEXT,             -- CE or PE
            ltp REAL,
            oi INTEGER,
            change_in_oi INTEGER,
            volume INTEGER,
            implied_volatility REAL,
            underlying_price REAL,
            snapshot_timestamp TEXT,      -- YYYY-MM-DD HH:MM:SS
            delta REAL,                   -- Computed Greeks
            gamma REAL,
            theta REAL,
            vega REAL,
            iv_percentile REAL,           -- Computed IV Percentile
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (symbol, expiry, strike, option_type, snapshot_timestamp)
        );
    """)
    
    # Create options_summary table
    # Primary key is (symbol, expiry, snapshot_timestamp) for aggregate metrics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS options_summary (
            symbol TEXT,
            expiry TEXT,                  -- YYYY-MM-DD
            snapshot_timestamp TEXT,      -- YYYY-MM-DD HH:MM:SS
            pcr REAL,                     -- Put-Call Ratio (Put OI / Call OI)
            underlying_price REAL,
            total_call_oi INTEGER,
            total_put_oi INTEGER,
            total_call_volume INTEGER,
            total_put_volume INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (symbol, expiry, snapshot_timestamp)
        );
    """)
    
    # Add indexes to speed up historical queries (e.g. IV history lookup)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_options_chain_history ON options_chain (symbol, expiry, strike, option_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_options_summary_history ON options_summary (symbol, expiry);")
    
    conn.commit()
    conn.close()
    print("Options schema migration completed successfully.")

if __name__ == "__main__":
    init_options_db()
