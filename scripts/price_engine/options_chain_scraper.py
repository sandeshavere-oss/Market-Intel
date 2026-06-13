import os
import sys
import argparse
import time
import json
import sqlite3
import random
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "price_data.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "options_scraper.log"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Reconfigure stdout to use UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def log_msg(level, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} [{level}] {msg}"
    print(log_line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"Failed to write log to file: {e}")

# Index mapping
INDEX_MAP = {
    "NIFTY50": "NIFTY",
    "NIFTY": "NIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "FINNIFTY": "FINNIFTY",
    "MIDCPNIFTY": "MIDCPNIFTY"
}

def is_index(symbol):
    return symbol.upper() in INDEX_MAP

def get_clean_symbol(symbol):
    sym_upper = symbol.upper()
    return INDEX_MAP.get(sym_upper, sym_upper)

def parse_expiry_date(date_str):
    """Converts DD-MM-YYYY or DD-MMM-YYYY to YYYY-MM-DD."""
    if not date_str:
        return ""
    try:
        # Check if format is DD-MM-YYYY (e.g. 30-06-2026)
        if "-" in date_str and len(date_str.split("-")[1]) == 2:
            dt = datetime.strptime(date_str, "%d-%m-%Y")
        else:
            # Format is DD-MMM-YYYY (e.g. 30-Jun-2026)
            dt = datetime.strptime(date_str, "%d-%b-%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        log_msg("WARNING", f"Failed to parse expiry date '{date_str}': {e}")
        return date_str

def parse_snapshot_timestamp(timestamp_str):
    """Converts DD-MMM-YYYY HH:MM:SS (e.g. 12-Jun-2026 15:30:00) to YYYY-MM-DD HH:MM:SS."""
    if not timestamp_str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        dt = datetime.strptime(timestamp_str, "%d-%b-%Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        log_msg("WARNING", f"Failed to parse snapshot timestamp '{timestamp_str}': {e}")
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def save_to_db(records_to_insert):
    if not records_to_insert:
        return
    
    max_retries = 5
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=60)
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            
            cursor.executemany("""
                INSERT OR REPLACE INTO options_chain (
                    symbol, expiry, strike, option_type, ltp, oi, change_in_oi, 
                    volume, implied_volatility, underlying_price, snapshot_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records_to_insert)
            
            conn.commit()
            log_msg("INFO", f"Saved/Updated {len(records_to_insert)} contract rows in options_chain table.")
            break
        except sqlite3.OperationalError as ex:
            if "locked" in str(ex).lower() and attempt < max_retries - 1:
                sleep_time = retry_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                log_msg("WARNING", f"Database locked, retrying in {sleep_time:.2f}s (attempt {attempt+1}/{max_retries}). Error: {ex}")
                time.sleep(sleep_time)
            else:
                log_msg("ERROR", f"Failed to save options data to database: {ex}")
                raise ex
        finally:
            if conn:
                conn.close()

def scrape_symbol(page, symbol, limit_expiries=None):
    clean_symbol = get_clean_symbol(symbol)
    symbol_type = "Indices" if is_index(symbol) else "Equities"
    
    log_msg("INFO", f"Scraping option chain for {symbol_type[:-3]} Symbol: {clean_symbol}")
    
    # 1. Fetch available expiries from contract-info API
    contract_info_url = f"https://www.nseindia.com/api/option-chain-contract-info?symbol={clean_symbol}"
    log_msg("INFO", f"Fetching contract metadata: {contract_info_url}")
    
    try:
        contract_info_str = page.evaluate("""
            async (url) => {
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return await response.text();
            }
        """, contract_info_url)
        
        contract_info = json.loads(contract_info_str)
        expiry_dates = contract_info.get("expiryDates", [])
        
        if not expiry_dates:
            log_msg("ERROR", f"No expiry dates returned for symbol {clean_symbol}. Response: {contract_info_str[:200]}")
            return False
            
        log_msg("INFO", f"Found {len(expiry_dates)} expiry dates: {expiry_dates}")
        
    except Exception as e:
        log_msg("ERROR", f"Failed to fetch contract metadata for {clean_symbol}: {e}")
        return False
    
    # Check if we should limit expiries (e.g. for testing)
    target_expiries = expiry_dates
    if limit_expiries and limit_expiries > 0:
        target_expiries = expiry_dates[:limit_expiries]
        log_msg("INFO", f"Limiting scrape to the nearest {limit_expiries} expiries: {target_expiries}")
        
    records_to_insert = []
    
    # 2. Loop through each expiry and fetch data
    for idx, expiry in enumerate(target_expiries):
        # Delay between requests to avoid rate limits
        if idx > 0:
            delay = random.uniform(2.0, 3.5)
            log_msg("INFO", f"Waiting {delay:.2f} seconds before requesting next expiry...")
            time.sleep(delay)
            
        api_url = f"https://www.nseindia.com/api/option-chain-v3?type={symbol_type}&symbol={clean_symbol}&expiry={expiry}"
        log_msg("INFO", f"Fetching Option Chain for expiry {expiry}: {api_url}")
        
        try:
            data_str = page.evaluate("""
                async (url) => {
                    const response = await fetch(url);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return await response.text();
                }
            """, api_url)
            
            data = json.loads(data_str)
            if "records" not in data or "data" not in data["records"]:
                log_msg("WARNING", f"No records/data found for expiry {expiry}. Got: {data_str[:200]}")
                continue
                
            records = data["records"]
            raw_timestamp = records.get("timestamp", "")
            snapshot_timestamp = parse_snapshot_timestamp(raw_timestamp)
            underlying_price = float(records.get("underlyingValue", 0.0))
            
            data_list = records.get("data", [])
            log_msg("INFO", f"Retrieved {len(data_list)} strikes for expiry {expiry}. Underlying price: {underlying_price}")
            
            expiry_inserted = 0
            for row in data_list:
                strike = float(row.get("strikePrice", 0.0))
                
                # Parse CE
                if "CE" in row and row["CE"] is not None:
                    ce = row["CE"]
                    standard_expiry = parse_expiry_date(ce.get("expiryDate"))
                    ltp = float(ce.get("lastPrice", 0.0))
                    oi = int(ce.get("openInterest", 0))
                    change_in_oi = int(ce.get("changeinOpenInterest", 0))
                    volume = int(ce.get("totalTradedVolume", 0))
                    iv = float(ce.get("impliedVolatility", 0.0))
                    
                    records_to_insert.append((
                        clean_symbol, standard_expiry, strike, "CE", ltp, oi,
                        change_in_oi, volume, iv, underlying_price, snapshot_timestamp
                    ))
                    expiry_inserted += 1
                    
                # Parse PE
                if "PE" in row and row["PE"] is not None:
                    pe = row["PE"]
                    standard_expiry = parse_expiry_date(pe.get("expiryDate"))
                    ltp = float(pe.get("lastPrice", 0.0))
                    oi = int(pe.get("openInterest", 0))
                    change_in_oi = int(pe.get("changeinOpenInterest", 0))
                    volume = int(pe.get("totalTradedVolume", 0))
                    iv = float(pe.get("impliedVolatility", 0.0))
                    
                    records_to_insert.append((
                        clean_symbol, standard_expiry, strike, "PE", ltp, oi,
                        change_in_oi, volume, iv, underlying_price, snapshot_timestamp
                    ))
                    expiry_inserted += 1
            
            log_msg("INFO", f"Processed {expiry_inserted} contract rows for expiry {expiry}.")
            
        except Exception as e:
            log_msg("ERROR", f"Failed to fetch/parse option chain for {clean_symbol} expiry {expiry}: {e}")
            
    # Save all parsed records to database
    if records_to_insert:
        save_to_db(records_to_insert)
        return True
    else:
        log_msg("WARNING", f"No records parsed for symbol {clean_symbol}.")
        return False

def main():
    parser = argparse.ArgumentParser(description="NSE Option Chain Scraper")
    parser.add_argument("--symbols", "-s", nargs="+", default=["NIFTY", "RELIANCE"], help="Symbols to scrape")
    parser.add_argument("--limit-expiries", "-l", type=int, default=3, help="Limit to nearest N expiries (default 3)")
    parser.add_argument("--headless", action="store_true", help="Launch Playwright in headless mode (default: headful)")
    args = parser.parse_args()
    
    log_msg("INFO", "Starting NSE Option Chain Scraper...")
    
    with sync_playwright() as p:
        # Default to headful (headless=False) because headful successfully bypasses bot protections
        headless_mode = args.headless
        log_msg("INFO", f"Launching Playwright Chromium (headless={headless_mode})")
        
        browser = p.chromium.launch(
            headless=headless_mode, 
            args=["--disable-http2"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        
        page = context.new_page()
        # Remove automated webdriver flags
        page.add_init_script("delete navigator.__proto__.webdriver;")
        
        option_chain_page = "https://www.nseindia.com/option-chain"
        log_msg("INFO", f"Visiting base option chain page: {option_chain_page}")
        
        try:
            page.goto(option_chain_page, wait_until="commit", timeout=20000)
            log_msg("INFO", "Base page headers committed, waiting 6 seconds for session cookies...")
            page.wait_for_timeout(6000)
            
            for idx, symbol in enumerate(args.symbols):
                if idx > 0:
                    delay = random.uniform(3.0, 5.0)
                    log_msg("INFO", f"Waiting {delay:.2f} seconds before scraping next symbol...")
                    time.sleep(delay)
                    
                try:
                    scrape_symbol(page, symbol, limit_expiries=args.limit_expiries)
                except Exception as sym_err:
                    log_msg("ERROR", f"Gracefully caught failure scraping symbol {symbol}: {sym_err}")
                    
        except Exception as page_err:
            log_msg("CRITICAL", f"Failed to initialize NSE session on base page: {page_err}")
            
        finally:
            browser.close()
            log_msg("INFO", "Scraper browser closed. Run complete.")

if __name__ == "__main__":
    main()
