import os
import sys
import sqlite3
import csv
from datetime import datetime
from pathlib import Path

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "price_data.db"
CSV_OUT = BASE_DIR / "data" / "reliance_pre_event_snapshot.csv"

# Reconfigure stdout to use UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def export_reliance_snapshot():
    print(f"Opening database to extract RELIANCE pre-event snapshot: {DB_PATH}")
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Get the latest snapshot timestamp for RELIANCE
    cursor.execute("""
        SELECT MAX(snapshot_timestamp) 
        FROM options_chain 
        WHERE symbol = 'RELIANCE'
    """)
    latest_snap = cursor.fetchone()[0]
    if not latest_snap:
        print("Error: No snapshots found for RELIANCE in database.")
        conn.close()
        sys.exit(1)
        
    print(f"Latest RELIANCE snapshot timestamp: {latest_snap}")
    
    # 2. Get the nearest expiry date for RELIANCE in this snapshot
    cursor.execute("""
        SELECT MIN(expiry) 
        FROM options_chain 
        WHERE symbol = 'RELIANCE' AND snapshot_timestamp = ?
    """, (latest_snap,))
    nearest_expiry = cursor.fetchone()[0]
    if not nearest_expiry:
        print("Error: No expiry dates found for RELIANCE.")
        conn.close()
        sys.exit(1)
        
    print(f"Nearest expiry date: {nearest_expiry}")
    
    # 3. Get the spot price (underlying Value)
    cursor.execute("""
        SELECT DISTINCT underlying_price 
        FROM options_chain 
        WHERE symbol = 'RELIANCE' AND snapshot_timestamp = ? AND expiry = ?
    """, (latest_snap, nearest_expiry))
    underlying_price = cursor.fetchone()[0]
    print(f"RELIANCE Spot Price: {underlying_price}")
    
    # 4. Fetch all available strikes for this expiry
    cursor.execute("""
        SELECT DISTINCT strike 
        FROM options_chain 
        WHERE symbol = 'RELIANCE' AND snapshot_timestamp = ? AND expiry = ?
        ORDER BY strike ASC
    """, (latest_snap, nearest_expiry))
    strikes = [row[0] for row in cursor.fetchall()]
    print(f"Total available strikes: {len(strikes)}")
    
    # 5. Find the ATM strike (closest to underlying price)
    atm_strike = min(strikes, key=lambda x: abs(x - underlying_price))
    atm_index = strikes.index(atm_strike)
    print(f"ATM Strike: {atm_strike} (Index {atm_index})")
    
    # 6. Select ATM and near-ATM strikes (ATM ± 5 strikes)
    start_idx = max(0, atm_index - 5)
    end_idx = min(len(strikes) - 1, atm_index + 5)
    target_strikes = strikes[start_idx:end_idx + 1]
    
    print(f"Selected {len(target_strikes)} strikes for the pre-event snapshot: {target_strikes}")
    
    # 7. Fetch full CE and PE details for these strikes
    snapshot_rows = []
    
    # Create directory for CSV output
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    
    for strike in target_strikes:
        # Fetch CE
        cursor.execute("""
            SELECT ltp, oi, change_in_oi, volume, implied_volatility, delta, gamma, theta, vega, iv_percentile
            FROM options_chain
            WHERE symbol = 'RELIANCE' AND snapshot_timestamp = ? AND expiry = ? AND strike = ? AND option_type = 'CE'
        """, (latest_snap, nearest_expiry, strike))
        ce_data = cursor.fetchone()
        
        # Fetch PE
        cursor.execute("""
            SELECT ltp, oi, change_in_oi, volume, implied_volatility, delta, gamma, theta, vega, iv_percentile
            FROM options_chain
            WHERE symbol = 'RELIANCE' AND snapshot_timestamp = ? AND expiry = ? AND strike = ? AND option_type = 'PE'
        """, (latest_snap, nearest_expiry, strike))
        pe_data = cursor.fetchone()
        
        ce_ltp, ce_oi, ce_coi, ce_vol, ce_iv, ce_delta, ce_gamma, ce_theta, ce_vega, ce_ivp = ce_data if ce_data else (0.0, 0, 0, 0, 0.0, None, None, None, None, None)
        pe_ltp, pe_oi, pe_coi, pe_vol, pe_iv, pe_delta, pe_gamma, pe_theta, pe_vega, pe_ivp = pe_data if pe_data else (0.0, 0, 0, 0, 0.0, None, None, None, None, None)
        
        snapshot_rows.append({
            "strike": strike,
            "ce_ltp": ce_ltp, "ce_oi": ce_oi, "ce_coi": ce_coi, "ce_vol": ce_vol, "ce_iv": ce_iv,
            "ce_delta": ce_delta, "ce_gamma": ce_gamma, "ce_theta": ce_theta, "ce_vega": ce_vega, "ce_ivp": ce_ivp,
            "pe_ltp": pe_ltp, "pe_oi": pe_oi, "pe_coi": pe_coi, "pe_vol": pe_vol, "pe_iv": pe_iv,
            "pe_delta": pe_delta, "pe_gamma": pe_gamma, "pe_theta": pe_theta, "pe_vega": pe_vega, "pe_ivp": pe_ivp,
        })
        
    # Write to CSV
    headers = [
        "strike", "ce_ltp", "ce_oi", "ce_coi", "ce_vol", "ce_iv", "ce_delta", "ce_gamma", "ce_theta", "ce_vega", "ce_ivp",
        "pe_ltp", "pe_oi", "pe_coi", "pe_vol", "pe_iv", "pe_delta", "pe_gamma", "pe_theta", "pe_vega", "pe_ivp"
    ]
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(snapshot_rows)
        
    print(f"Pre-event snapshot saved to: {CSV_OUT}")
    
    # 8. Print formatted markdown table for copy-paste
    print("\nMARKDOWN TABLE FOR RELIANCE PRE-EVENT SNAPSHOT:")
    print(f"### RELIANCE Pre-Event Option Chain Snapshot (Spot: {underlying_price} | Expiry: {nearest_expiry} | Snapshot Time: {latest_snap})")
    print("| Strike | CE LTP | CE OI | CE IV (%) | CE Delta | CE Gamma | CE Vega | CE Theta | PE LTP | PE OI | PE IV (%) | PE Delta | PE Gamma | PE Vega | PE Theta |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    
    for row in snapshot_rows:
        strike = row["strike"]
        # Format CE Greeks
        ce_d = f"{row['ce_delta']:.4f}" if row['ce_delta'] is not None else "N/A"
        ce_g = f"{row['ce_gamma']:.6f}" if row['ce_gamma'] is not None else "N/A"
        ce_v = f"{row['ce_vega']:.4f}" if row['ce_vega'] is not None else "N/A"
        ce_t = f"{row['ce_theta']:.4f}" if row['ce_theta'] is not None else "N/A"
        # Format PE Greeks
        pe_d = f"{row['pe_delta']:.4f}" if row['pe_delta'] is not None else "N/A"
        pe_g = f"{row['pe_gamma']:.6f}" if row['pe_gamma'] is not None else "N/A"
        pe_v = f"{row['pe_vega']:.4f}" if row['pe_vega'] is not None else "N/A"
        pe_t = f"{row['pe_theta']:.4f}" if row['pe_theta'] is not None else "N/A"
        
        # Display ATM flag
        strike_label = f"**{strike} (ATM)**" if strike == atm_strike else f"{strike}"
        
        print(f"| {strike_label} | {row['ce_ltp']} | {row['ce_oi']} | {row['ce_iv']}% | {ce_d} | {ce_g} | {ce_v} | {ce_t} | {row['pe_ltp']} | {row['pe_oi']} | {row['pe_iv']}% | {pe_d} | {pe_g} | {pe_v} | {pe_t} |")

    # Fetch PCR summary
    cursor.execute("""
        SELECT pcr, total_call_oi, total_put_oi, total_call_volume, total_put_volume
        FROM options_summary
        WHERE symbol = 'RELIANCE' AND expiry = ? AND snapshot_timestamp = ?
    """, (nearest_expiry, latest_snap))
    summary = cursor.fetchone()
    if summary:
        pcr, call_oi, put_oi, call_vol, put_vol = summary
        print(f"\n**Summary Metrics:**")
        print(f"* **Total Call OI:** {call_oi} contracts")
        print(f"* **Total Put OI:** {put_oi} contracts")
        print(f"* **Put-Call Ratio (PCR) by OI:** {pcr:.4f}")
        print(f"* **Total Call Volume:** {call_vol} contracts")
        print(f"* **Total Put Volume:** {put_vol} contracts")
        
    conn.close()

if __name__ == "__main__":
    export_reliance_snapshot()
