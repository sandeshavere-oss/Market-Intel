import os
import sys
import math
import sqlite3
import argparse
import random
from datetime import datetime
from pathlib import Path

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "price_data.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "greeks_calculator.log"

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

def get_clean_symbol(symbol):
    sym_upper = symbol.upper()
    return INDEX_MAP.get(sym_upper, sym_upper)

# Standard Normal Distribution functions
def norm_cdf(x):
    """Cumulative distribution function for standard normal distribution."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x):
    """Probability density function for standard normal distribution."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

# Black-Scholes Formula for European Options Greeks
def calculate_bs_greeks(S, K, days_to_expiry, iv_pct, r_pct=6.5, option_type="CE"):
    """
    Calculates Black-Scholes Greeks: Delta, Gamma, Theta, Vega.
    S: Underlying price (Spot)
    K: Strike price
    days_to_expiry: Days to expiration
    iv_pct: Implied Volatility (in percentage, e.g. 18.5)
    r_pct: Risk-free rate (in percentage, e.g. 6.5)
    option_type: 'CE' (Call) or 'PE' (Put)
    """
    # Boundary cases:
    T = days_to_expiry / 365.0
    sigma = iv_pct / 100.0
    r = r_pct / 100.0
    
    # 1. Handle expired options or extremely close to expiry
    if T <= 1e-6:
        # Intrinsic delta
        if option_type == "CE":
            delta = 1.0 if S > K else (0.5 if S == K else 0.0)
        else:
            delta = -1.0 if S < K else (-0.5 if S == K else 0.0)
        return delta, 0.0, 0.0, 0.0
        
    # 2. Handle missing or zero implied volatility
    if sigma <= 1e-4:
        return None, None, None, None
        
    try:
        # Calculate d1 and d2
        d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        # Calculate N(d1), N(d2), N'(d1)
        n_d1 = norm_cdf(d1)
        n_d2 = norm_cdf(d2)
        n_prime_d1 = norm_pdf(d1)
        
        # 1. Delta
        if option_type == "CE":
            delta = n_d1
        else:
            delta = n_d1 - 1.0
            
        # 2. Gamma (same for Call and Put)
        gamma = n_prime_d1 / (S * sigma * math.sqrt(T))
        
        # 3. Vega (same for Call and Put)
        # Standard Vega is dV/dSigma. Usually divided by 100 to show change per 1% vol change.
        vega = (S * math.sqrt(T) * n_prime_d1) / 100.0
        
        # 4. Theta (daily decay = Annual Theta / 365)
        term1 = -(S * n_prime_d1 * sigma) / (2.0 * math.sqrt(T))
        if option_type == "CE":
            term2 = -r * K * math.exp(-r * T) * n_d2
        else:
            term2 = r * K * math.exp(-r * T) * norm_cdf(-d2)
            
        annual_theta = term1 + term2
        daily_theta = annual_theta / 365.0
        
        return delta, gamma, daily_theta, vega
        
    except Exception as e:
        log_msg("WARNING", f"Error calculating Greeks: {e}")
        return None, None, None, None

def get_latest_snapshots(conn, symbols):
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in symbols)
    
    # Query latest snapshot timestamp per symbol
    cursor.execute(f"""
        SELECT symbol, MAX(snapshot_timestamp) 
        FROM options_chain 
        WHERE symbol IN ({placeholders})
        GROUP BY symbol
    """, symbols)
    
    return {row[0]: row[1] for row in cursor.fetchall()}

def get_all_snapshots_in_db(conn, symbols):
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in symbols)
    
    cursor.execute(f"""
        SELECT DISTINCT symbol, snapshot_timestamp 
        FROM options_chain 
        WHERE symbol IN ({placeholders})
    """, symbols)
    
    return cursor.fetchall()

def process_snapshot_greeks(conn, symbol, snapshot_timestamp, r_rate, min_history_points=5):
    cursor = conn.cursor()
    
    # 1. Retrieve all contract rows for this snapshot
    cursor.execute("""
        SELECT expiry, strike, option_type, ltp, oi, change_in_oi, volume, 
               implied_volatility, underlying_price
        FROM options_chain
        WHERE symbol = ? AND snapshot_timestamp = ?
    """, (symbol, snapshot_timestamp))
    
    rows = cursor.fetchall()
    if not rows:
        return
        
    log_msg("INFO", f"Processing Greeks for {symbol} at {snapshot_timestamp} ({len(rows)} contracts)...")
    
    # Group rows by expiry for PCR and summary calculations
    by_expiry = {}
    for r in rows:
        expiry = r[0]
        if expiry not in by_expiry:
            by_expiry[expiry] = []
        by_expiry[expiry].append(r)
        
    greeks_updates = []
    summary_inserts = []
    
    snap_dt = datetime.strptime(snapshot_timestamp, "%Y-%m-%d %H:%M:%S")
    
    for expiry, exp_rows in by_expiry.items():
        exp_date = datetime.strptime(expiry, "%Y-%m-%d").date()
        days_to_expiry = max(0, (exp_date - snap_dt.date()).days)
        
        # Calculate PCR and other aggregate metrics for options_summary
        total_call_oi = 0
        total_put_oi = 0
        total_call_vol = 0
        total_put_vol = 0
        underlying_price = 0.0
        
        for r in exp_rows:
            strike = r[1]
            opt_type = r[2]
            oi = r[4]
            vol = r[6]
            iv = r[7]
            underlying_price = r[8]  # Should be same across all rows of the snapshot
            
            if opt_type == "CE":
                total_call_oi += oi
                total_call_vol += vol
            else:
                total_put_oi += oi
                total_put_vol += vol
                
            # Compute Black-Scholes Greeks
            delta, gamma, theta, vega = calculate_bs_greeks(
                underlying_price, strike, days_to_expiry, iv, r_pct=r_rate, option_type=opt_type
            )
            
            # Compute IV Percentile
            # Fetch historical IVs for this specific contract
            cursor.execute("""
                SELECT implied_volatility 
                FROM options_chain 
                WHERE symbol = ? AND expiry = ? AND strike = ? AND option_type = ? AND snapshot_timestamp <= ?
                ORDER BY snapshot_timestamp ASC
            """, (symbol, expiry, strike, opt_type, snapshot_timestamp))
            
            history_ivs = [h[0] for h in cursor.fetchall() if h[0] > 0.0]
            
            iv_percentile = None
            if len(history_ivs) >= min_history_points and iv > 0.0:
                less_equal = sum(1 for h in history_ivs if h <= iv)
                iv_percentile = (less_equal / len(history_ivs)) * 100.0
                
            greeks_updates.append((
                delta, gamma, theta, vega, iv_percentile,
                symbol, expiry, strike, opt_type, snapshot_timestamp
            ))
            
        # Calculate PCR (Put-Call Ratio by Open Interest)
        pcr = None
        if total_call_oi > 0:
            pcr = float(total_put_oi) / float(total_call_oi)
            
        summary_inserts.append((
            symbol, expiry, snapshot_timestamp, pcr, underlying_price,
            total_call_oi, total_put_oi, total_call_vol, total_put_vol
        ))
        
    # Write Updates back to options_chain
    if greeks_updates:
        cursor.executemany("""
            UPDATE options_chain
            SET delta = ?, gamma = ?, theta = ?, vega = ?, iv_percentile = ?
            WHERE symbol = ? AND expiry = ? AND strike = ? AND option_type = ? AND snapshot_timestamp = ?
        """, greeks_updates)
        
    # Write Inserts/Updates to options_summary
    if summary_inserts:
        cursor.executemany("""
            INSERT OR REPLACE INTO options_summary (
                symbol, expiry, snapshot_timestamp, pcr, underlying_price,
                total_call_oi, total_put_oi, total_call_volume, total_put_volume
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, summary_inserts)
        
    conn.commit()
    log_msg("INFO", f"Successfully computed and saved Greeks & PCR for {symbol} at {snapshot_timestamp}.")

def main():
    parser = argparse.ArgumentParser(description="Options Greeks & PCR Calculator")
    parser.add_argument("--symbols", "-s", nargs="+", default=["NIFTY", "RELIANCE"], help="Symbols to process")
    parser.add_argument("--all-snapshots", action="store_true", help="Process all snapshots in the DB instead of only the latest")
    parser.add_argument("--snapshot", "-t", type=str, help="Specific snapshot timestamp to process (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--risk-free-rate", "-r", type=float, default=6.5, help="Risk free rate as percentage (default: 6.5)")
    parser.add_argument("--min-history", type=int, default=5, help="Minimum history data points for IV percentile (default: 5)")
    args = parser.parse_args()
    
    log_msg("INFO", "Starting Option Greeks Calculator...")
    
    if not DB_PATH.exists():
        log_msg("ERROR", f"Price database not found at {DB_PATH}. Run migration and scraper first.")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Determine snapshots to process
        symbols_to_process = [get_clean_symbol(s) for s in args.symbols]
        
        snapshots_to_process = []
        if args.snapshot:
            # Process a specific snapshot
            for sym in symbols_to_process:
                snapshots_to_process.append((sym, args.snapshot))
        elif args.all_snapshots:
            # Process all historical snapshots
            snapshots_to_process = get_all_snapshots_in_db(conn, symbols_to_process)
            log_msg("INFO", f"Found {len(snapshots_to_process)} historical snapshots to process.")
        else:
            # Default: Process only the latest snapshot for each symbol
            latest_snaps = get_latest_snapshots(conn, symbols_to_process)
            for sym, snap in latest_snaps.items():
                if snap:
                    snapshots_to_process.append((sym, snap))
            log_msg("INFO", f"Identified latest snapshots: {latest_snaps}")
            
        if not snapshots_to_process:
            log_msg("WARNING", "No snapshots found to process in database.")
            return
            
        for sym, snap_timestamp in snapshots_to_process:
            process_snapshot_greeks(
                conn, sym, snap_timestamp, args.risk_free_rate, min_history_points=args.min_history
            )
            
    except Exception as e:
        log_msg("CRITICAL", f"Greeks calculation failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        log_msg("INFO", "Greeks Calculator run complete.")

if __name__ == "__main__":
    main()
