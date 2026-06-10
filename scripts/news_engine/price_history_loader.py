import os
import sqlite3
import csv
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import requests
import yfinance as yf

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "price_data.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "price_history_loader.log"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Reconfigure stdout to use UTF-8 (prevents crashes with emojis/special characters)
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
    log_message("INFO", f"Initializing price_history table in database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable WAL mode for database concurrency
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Create the requested price_history table schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            symbol TEXT,
            trade_date DATE,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (symbol, trade_date)
        )
    """)
    conn.commit()
    conn.close()

def fetch_nifty50_symbols():
    url = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    log_message("INFO", f"Fetching Nifty 50 list from: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        lines = response.text.splitlines()
        reader = csv.DictReader(lines)
        symbols = [row["Symbol"].strip() for row in reader if row.get("Symbol")]
        log_message("INFO", f"Fetched {len(symbols)} Nifty 50 symbols.")
        return symbols
    except Exception as e:
        log_message("ERROR", f"Failed to fetch Nifty 50 list: {e}")
        return []

def fetch_niftynext50_symbols():
    url = "https://archives.nseindia.com/content/indices/ind_niftynext50list.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    log_message("INFO", f"Fetching Nifty Next 50 list from: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        lines = response.text.splitlines()
        reader = csv.DictReader(lines)
        symbols = [row["Symbol"].strip() for row in reader if row.get("Symbol")]
        # Filter symbols to keep only valid uppercase strings
        symbols = [s for s in symbols if s.isupper() and len(s) > 1]
        log_message("INFO", f"Fetched {len(symbols)} Nifty Next 50 symbols.")
        return symbols
    except Exception as e:
        log_message("ERROR", f"Failed to fetch Nifty Next 50 list: {e}")
        return []

def fetch_fo_symbols():
    url = "https://api.kite.trade/instruments"
    log_message("INFO", f"Fetching F&O list from Zerodha Kite API: {url}")
    try:
        response = requests.get(url, timeout=30)
        lines = response.text.splitlines()
        reader = csv.DictReader(lines)
        symbols = set(row["name"].strip() for row in reader if row.get("exchange") == "NFO" and row.get("segment") == "NFO-FUT")
        log_message("INFO", f"Fetched {len(symbols)} F&O symbols.")
        return list(symbols)
    except Exception as e:
        log_message("ERROR", f"Failed to fetch F&O list from Kite API: {e}")
        return []

def fetch_and_store_history(days_back=180):
    init_db()
    
    # 1. Collect all target lists
    n50 = fetch_nifty50_symbols()
    nnext50 = fetch_niftynext50_symbols()
    fo = fetch_fo_symbols()
    
    # Combine into unique set
    all_symbols = set(n50 + nnext50 + fo)
    symbols = sorted(list(all_symbols))
    
    log_message("INFO", f"Combined total of {len(symbols)} unique symbols to download (overlapping duplicates removed).")
    
    if not symbols:
        log_message("ERROR", "No symbols collected. Exiting.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Date range
    end_date = datetime.now() + timedelta(days=1)
    start_date = datetime.now() - timedelta(days=days_back)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    log_message("INFO", f"Downloading price history from {start_str} to {end_str}")
    
    batch_size = 20
    total_inserted = 0
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        # Map yfinance tickers back to database symbol
        ticker_map = {f"{sym}.NS": sym for sym in batch}
        
        log_message("INFO", f"Downloading batch {i//batch_size + 1}/{len(symbols)//batch_size + 1}: {list(ticker_map.keys())}")
        
        try:
            data = yf.download(list(ticker_map.keys()), start=start_str, end=end_str, group_by='ticker', progress=False)
            
            for ticker, sym in ticker_map.items():
                # Extract individual ticker data frame
                if len(batch) == 1:
                    ticker_df = data
                else:
                    if ticker not in data.columns.levels[0] if hasattr(data.columns, 'levels') else True:
                        continue
                    ticker_df = data[ticker]
                    
                if ticker_df.empty:
                    continue
                    
                # Drop rows with empty Close prices
                ticker_df = ticker_df.dropna(subset=['Close'])
                
                rows_to_insert = []
                for date, row in ticker_df.iterrows():
                    date_str = date.strftime("%Y-%m-%d")
                    rows_to_insert.append((
                        sym,
                        date_str,
                        float(row['Open']),
                        float(row['High']),
                        float(row['Low']),
                        float(row['Close']),
                        int(row['Volume'])
                    ))
                    
                if rows_to_insert:
                    cursor.executemany("""
                        INSERT OR REPLACE INTO price_history (symbol, trade_date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, rows_to_insert)
                    total_inserted += len(rows_to_insert)
                    
            conn.commit()
            log_message("INFO", f"Batch {i//batch_size + 1} completed and saved.")
        except Exception as e:
            log_message("ERROR", f"Error downloading batch {i//batch_size + 1}: {e}")
            
    conn.close()
    log_message("INFO", f"Price history collection completed. Total rows saved: {total_inserted}")

def main():
    parser = argparse.ArgumentParser(description="Market Intel Price History Downloader")
    parser.add_argument("--backfill", type=int, default=180, help="Number of days of history to download")
    args = parser.parse_args()
    
    fetch_and_store_history(days_back=args.backfill)

if __name__ == "__main__":
    main()
