import os
import sqlite3
import csv
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "price_data.db"
MASTER_FILE = BASE_DIR / "data" / "mappings" / "company_master.csv"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "price_engine.log"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Logging setup
def log_message(level, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} [{level}] {msg}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

def init_db():
    log_message("INFO", f"Initializing price database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_prices (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.commit()
    conn.close()

def load_symbols():
    symbols = []
    if not MASTER_FILE.exists():
        log_message("ERROR", f"company_master.csv not found at {MASTER_FILE}")
        return symbols
    try:
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row.get("symbol", "").strip()
                if symbol and symbol not in symbols:
                    symbols.append(symbol)
    except Exception as e:
        log_message("ERROR", f"Failed to load symbols: {e}")
    return symbols

def fetch_and_store_prices(symbols, days_back=180):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    end_date = datetime.now() + timedelta(days=1)
    start_date = datetime.now() - timedelta(days=days_back)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    log_message("INFO", f"Fetching prices from {start_str} to {end_str} for {len(symbols)} symbols")

    # Batching to avoid API rate limiting and connection issues
    batch_size = 20
    total_inserted = 0

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        # Append .NS suffix for Indian NSE markets
        ticker_map = {f"{sym}.NS": sym for sym in batch}
        tickers_str = " ".join(ticker_map.keys())

        log_message("INFO", f"Downloading batch {i//batch_size + 1}: {tickers_str}")
        try:
            # Download batch
            data = yf.download(list(ticker_map.keys()), start=start_str, end=end_str, group_by='ticker', progress=False)
            
            for ticker, sym in ticker_map.items():
                # Extract ticker dataframe
                if ticker not in data.columns.levels[0] if isinstance(data.columns, argparse.Namespace) or hasattr(data.columns, 'levels') else True:
                    # If only one ticker was returned, the dataframe format might be flat
                    if len(batch) == 1:
                        ticker_df = data
                    else:
                        continue
                else:
                    ticker_df = data[ticker]

                if ticker_df.empty:
                    continue

                # Drop NaNs and iterate
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
                        INSERT OR REPLACE INTO daily_prices (symbol, date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, rows_to_insert)
                    total_inserted += len(rows_to_insert)
            
            conn.commit()
            log_message("INFO", f"Batch {i//batch_size + 1} completed and saved.")
        except Exception as e:
            log_message("ERROR", f"Error fetching batch {i//batch_size + 1}: {e}")

    conn.close()
    log_message("INFO", f"Price engine run completed. Total records saved/updated: {total_inserted}")

def main():
    parser = argparse.ArgumentParser(description="Market Intel Price Data Engine")
    parser.add_argument("--backfill", type=int, default=180, help="Number of days of history to fetch")
    args = parser.parse_args()

    symbols = load_symbols()
    if not symbols:
        log_message("ERROR", "No symbols loaded. Exiting.")
        sys.exit(1)

    fetch_and_store_prices(symbols, days_back=args.backfill)

if __name__ == "__main__":
    main()
