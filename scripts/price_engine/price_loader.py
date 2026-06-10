import os
import sqlite3
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf

# Resolve paths relative to this script
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "price_data.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "price_engine.log"
MASTER_FILE = BASE_DIR / "data" / "mappings" / "company_master.csv"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Reconfigure stdout to use UTF-8
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
    log_message("INFO", f"Initializing price database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Check if table price_history already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_history'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        # Check schema of price_history
        cursor.execute("PRAGMA table_info(price_history)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        # If columns contain 'trade_date' instead of 'date', we migrate (legacy fallback)
        if "trade_date" in columns and "date" not in columns:
            log_message("INFO", "Migrating legacy price_history table schema (trade_date -> date)...")
            try:
                # Rename the old table
                cursor.execute("ALTER TABLE price_history RENAME TO price_history_old;")
                
                # Create the new table with the requested schema
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS price_history (
                        symbol TEXT,
                        date TEXT,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        adj_close REAL,
                        volume INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY(symbol,date)
                    );
                """)
                
                # Copy data from old table to new table (default adj_close to close)
                cursor.execute("""
                    INSERT OR IGNORE INTO price_history (symbol, date, open, high, low, close, adj_close, volume)
                    SELECT symbol, trade_date, open, high, low, close, close, volume FROM price_history_old;
                """)
                
                # Drop old table
                cursor.execute("DROP TABLE price_history_old;")
                conn.commit()
                log_message("INFO", "Legacy schema migration of price_history completed successfully.")
            except Exception as e:
                conn.rollback()
                log_message("ERROR", f"Failed to migrate legacy price_history schema: {e}")
                raise e
        else:
            # If adj_close column is missing, add it
            if "adj_close" not in columns:
                log_message("INFO", "Adding missing adj_close column to price_history table...")
                try:
                    cursor.execute("ALTER TABLE price_history ADD COLUMN adj_close REAL;")
                    cursor.execute("UPDATE price_history SET adj_close = close WHERE adj_close IS NULL;")
                    conn.commit()
                    log_message("INFO", "adj_close column added and backfilled successfully.")
                except Exception as e:
                    conn.rollback()
                    log_message("ERROR", f"Failed to add adj_close column: {e}")
                    raise e
    else:
        # Create table if it doesn't exist at all
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                symbol TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(symbol,date)
            );
        """)
        conn.commit()
        
    # Also, if a daily_prices table exists, let's copy its data into price_history
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_prices'")
    daily_prices_exists = cursor.fetchone()
    if daily_prices_exists:
        log_message("INFO", "Syncing existing daily_prices table data to price_history...")
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO price_history (symbol, date, open, high, low, close, adj_close, volume)
                SELECT symbol, date, open, high, low, close, close, volume FROM daily_prices;
            """)
            conn.commit()
            log_message("INFO", "Synced daily_prices data successfully.")
        except Exception as e:
            conn.rollback()
            log_message("ERROR", f"Failed to sync daily_prices data: {e}")
            
    conn.close()

def load_universe_symbols():
    if not MASTER_FILE.exists():
        log_message("ERROR", f"Company master file not found at: {MASTER_FILE}")
        return []
    
    symbols = []
    try:
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sym = row.get("symbol", "").strip()
                if sym:
                    symbols.append(sym)
        log_message("INFO", f"Loaded {len(symbols)} symbols from company master.")
        return sorted(list(set(symbols)))
    except Exception as e:
        log_message("ERROR", f"Failed to read company master: {e}")
        return []

def get_latest_dates():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, MAX(date) FROM price_history GROUP BY symbol")
    dates = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return dates

def download_and_store():
    # 1. Initialize DB and ensure correct schema
    init_db()
    
    # 2. Load universe symbols
    symbols = load_universe_symbols()
    if not symbols:
        log_message("ERROR", "No symbols to process. Exiting.")
        return
        
    # 3. Get latest dates for each symbol to determine incremental downloads
    latest_dates = get_latest_dates()
    
    # We will process symbols in batches to speed up yfinance requests
    batch_size = 20
    total_records_saved = 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # We want data up to today. yfinance end date is exclusive, so use tomorrow.
    tomorrow_dt = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow_dt.strftime("%Y-%m-%d")
    
    # Default lookback if no data exists
    default_start_dt = datetime.now() - timedelta(days=365)
    default_start_str = default_start_dt.strftime("%Y-%m-%d")
    
    # Group symbols by their start date to batch them efficiently
    start_date_groups = {}
    for sym in symbols:
        # Check if symbol already exists for a date
        max_date = latest_dates.get(sym)
        if max_date:
            # If max_date is today or later, we don't need to download
            max_date_dt = datetime.strptime(max_date, "%Y-%m-%d")
            # If max_date is today, we skip download for this symbol
            if max_date_dt.date() >= datetime.now().date():
                continue
            # Increment by 1 day to fetch only new data
            start_dt = max_date_dt + timedelta(days=1)
            start_str = start_dt.strftime("%Y-%m-%d")
        else:
            start_str = default_start_str
            
        start_date_groups.setdefault(start_str, []).append(sym)
        
    log_message("INFO", f"Prepared {len(symbols)} symbols for download across {len(start_date_groups)} date groups.")
    
    for start_str, syms in start_date_groups.items():
        # Check if we should skip because start_str is in the future
        start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        if start_dt.date() > datetime.now().date():
            continue
            
        log_message("INFO", f"Downloading prices from {start_str} to {tomorrow_str} for {len(syms)} symbols...")
        
        # Batch symbols in chunks of batch_size
        for i in range(0, len(syms), batch_size):
            chunk = syms[i:i + batch_size]
            ticker_map = {}
            for sym in chunk:
                if sym == "NIFTY50":
                    ticker_map["^NSEI"] = "NIFTY50"
                else:
                    ticker_map[f"{sym}.NS"] = sym
            tickers_str = " ".join(ticker_map.keys())
            
            log_message("INFO", f"Downloading batch: {tickers_str}")
            
            try:
                # yfinance download
                data = yf.download(
                    list(ticker_map.keys()),
                    start=start_str,
                    end=tomorrow_str,
                    group_by='ticker',
                    progress=False
                )
                
                rows_to_insert = []
                
                for ticker, sym in ticker_map.items():
                    # Handle single ticker DataFrame vs MultiIndex DataFrame
                    if len(chunk) == 1:
                        ticker_df = data
                    else:
                        if ticker not in data.columns.levels[0] if hasattr(data.columns, 'levels') else True:
                            continue
                        ticker_df = data[ticker]
                        
                    if ticker_df.empty:
                        continue
                        
                    # Drop rows with empty Close prices
                    ticker_df = ticker_df.dropna(subset=['Close'])
                    
                    for date, row in ticker_df.iterrows():
                        date_str = date.strftime("%Y-%m-%d")
                        
                        # Double-check: if a symbol already exists for a date, skip
                        # Although INSERT OR IGNORE will do this, we can also let sqlite handle it
                        rows_to_insert.append((
                            sym,
                            date_str,
                            float(row['Open']),
                            float(row['High']),
                            float(row['Low']),
                            float(row['Close']),
                            float(row['Adj Close']) if 'Adj Close' in row.index else float(row['Close']),
                            int(row['Volume'])
                        ))
                
                if rows_to_insert:
                    cursor.executemany("""
                        INSERT OR IGNORE INTO price_history (symbol, date, open, high, low, close, adj_close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, rows_to_insert)
                    conn.commit()
                    total_records_saved += len(rows_to_insert)
                    log_message("INFO", f"Saved {len(rows_to_insert)} records for batch.")
                else:
                    log_message("INFO", "No new records to save in this batch.")
                    
            except Exception as e:
                log_message("ERROR", f"Failed to download/process batch: {e}")
                
    conn.close()
    log_message("INFO", f"Price engine run completed. Total records saved/updated: {total_records_saved}")

if __name__ == "__main__":
    download_and_store()
