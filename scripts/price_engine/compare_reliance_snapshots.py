import os
import sys
import math
import sqlite3
import csv
from datetime import datetime
from pathlib import Path

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "price_data.db"
CSV_PRE = BASE_DIR / "data" / "reliance_pre_event_snapshot.csv"
CSV_OUT = BASE_DIR / "data" / "reliance_before_after_comparison.csv"

# Reconfigure stdout to use UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def norm_cdf(x):
    """Cumulative distribution function for standard normal distribution."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def calculate_bs_price(S, K, days_to_expiry, iv_pct, r_pct=6.5, option_type="CE"):
    """Calculates Black-Scholes option price for European option."""
    T = days_to_expiry / 365.0
    sigma = iv_pct / 100.0
    r = r_pct / 100.0
    
    if T <= 0.0:
        if option_type == "CE":
            return max(0.0, S - K)
        else:
            return max(0.0, K - S)
            
    if sigma <= 0.0:
        if option_type == "CE":
            return max(0.0, S - K * math.exp(-r * T))
        else:
            return max(0.0, K * math.exp(-r * T) - S)
            
    try:
        d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        if option_type == "CE":
            price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        else:
            price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        return price
    except Exception as e:
        print(f"Error pricing option: {e}")
        return 0.0

def load_pre_event_snapshot():
    if not CSV_PRE.exists():
        print(f"Error: Pre-event snapshot not found at {CSV_PRE}")
        sys.exit(1)
        
    pre_data = {}
    with open(CSV_PRE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            strike = float(row["strike"])
            pre_data[strike] = {
                "ce_ltp": float(row["ce_ltp"]),
                "ce_oi": int(row["ce_oi"]),
                "ce_iv": float(row["ce_iv"]),
                "ce_delta": float(row["ce_delta"]) if row["ce_delta"] else 0.0,
                "pe_ltp": float(row["pe_ltp"]),
                "pe_oi": int(row["pe_oi"]),
                "pe_iv": float(row["pe_iv"]),
                "pe_delta": float(row["pe_delta"]) if row["pe_delta"] else 0.0,
            }
    return pre_data

def query_post_event_data():
    if not DB_PATH.exists():
        return None, None
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if we have snapshots on or after June 15, 2026
    cursor.execute("""
        SELECT DISTINCT snapshot_timestamp 
        FROM options_chain 
        WHERE symbol = 'RELIANCE' AND date(snapshot_timestamp) >= '2026-06-15'
        ORDER BY snapshot_timestamp ASC
        LIMIT 1
    """)
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None, None
        
    post_ts = row[0]
    
    # Get the nearest expiry in that post-event snapshot
    cursor.execute("""
        SELECT MIN(expiry) 
        FROM options_chain 
        WHERE symbol = 'RELIANCE' AND snapshot_timestamp = ?
    """, (post_ts,))
    expiry_row = cursor.fetchone()
    post_expiry = expiry_row[0] if expiry_row else None
    if not post_expiry:
        conn.close()
        return None, None
        
    # Get spot price
    cursor.execute("""
        SELECT DISTINCT underlying_price 
        FROM options_chain 
        WHERE symbol = 'RELIANCE' AND snapshot_timestamp = ? AND expiry = ?
    """, (post_ts, post_expiry))
    spot_row = cursor.fetchone()
    post_spot = spot_row[0] if spot_row else 0.0
    
    # Load option chain rows for post-event
    cursor.execute("""
        SELECT strike, option_type, ltp, oi, implied_volatility, delta
        FROM options_chain
        WHERE symbol = 'RELIANCE' AND snapshot_timestamp = ? AND expiry = ?
    """, (post_ts, post_expiry))
    
    post_data = {}
    for strike, opt_type, ltp, oi, iv, delta in cursor.fetchall():
        s = float(strike)
        if s not in post_data:
            post_data[s] = {}
        if opt_type == "CE":
            post_data[s]["ce_ltp"] = ltp
            post_data[s]["ce_oi"] = oi
            post_data[s]["ce_iv"] = iv
            post_data[s]["ce_delta"] = delta
        else:
            post_data[s]["pe_ltp"] = ltp
            post_data[s]["pe_oi"] = oi
            post_data[s]["pe_iv"] = iv
            post_data[s]["pe_delta"] = delta
            
    conn.close()
    return post_data, {"timestamp": post_ts, "expiry": post_expiry, "spot": post_spot}

def run_simulation(pre_data):
    """
    Simulates the post-event options values after a 4-day holding period (from June 12 to June 16)
    with a severe IV crush from 25.11% pre-event to 15.0% post-event.
    """
    print("\nNo actual post-event data found in database. Running Volatility Crush Simulation...")
    print("Baseline parameters:")
    print("  - Pre-Event: Date: 2026-06-12 | Spot: 1296.4 | IV: ~25.1% | Days to Expiry: 18")
    print("  - Post-Event Simulation: Date: 2026-06-16 | Days to Expiry: 14 | IV: 15.0% | Risk-Free: 6.5%")
    
    # Scenario details
    scenarios = [
        {"name": "Scenario A: Spot Unchanged", "spot": 1296.40, "desc": "Spot remains exactly at 1296.4"},
        {"name": "Scenario B: Spot Up 2.0%", "spot": 1322.33, "desc": "Spot rises by 2.0% (bullish move)"},
        {"name": "Scenario C: Spot Down 2.0%", "spot": 1270.47, "desc": "Spot drops by 2.0% (bearish move)"}
    ]
    
    sim_results = {}
    
    for strike, pre in pre_data.items():
        sim_results[strike] = {
            "ce_pre_ltp": pre["ce_ltp"],
            "pe_pre_ltp": pre["pe_ltp"],
            "ce_pre_iv": pre["ce_iv"],
            "pe_pre_iv": pre["pe_iv"]
        }
        
        # Calculate for each scenario
        for sc in scenarios:
            name = sc["name"]
            spot = sc["spot"]
            
            # CE post-event theoretical price
            ce_post_price = calculate_bs_price(spot, strike, 14, 15.0, r_pct=6.5, option_type="CE")
            # PE post-event theoretical price
            pe_post_price = calculate_bs_price(spot, strike, 14, 15.0, r_pct=6.5, option_type="PE")
            
            # CE Return
            ce_ret = (ce_post_price - pre["ce_ltp"]) / pre["ce_ltp"] if pre["ce_ltp"] > 0 else 0.0
            # PE Return
            pe_ret = (pe_post_price - pre["pe_ltp"]) / pre["pe_ltp"] if pre["pe_ltp"] > 0 else 0.0
            
            sim_results[strike][f"ce_{name}_price"] = ce_post_price
            sim_results[strike][f"pe_{name}_price"] = pe_post_price
            sim_results[strike][f"ce_{name}_return"] = ce_ret
            sim_results[strike][f"pe_{name}_return"] = pe_ret
            
    # Print comparison table for Scenario B (Spot Up 2.0% - Bullish)
    print("\n--- SIMULATION RESULTS: Scenario B (Spot Rises 2% to 1322.33, IV Crushes to 15.0%) ---")
    print("Under a standard Call signal, a 2% spot rise should be highly profitable. Let's see the IV Crush impact:")
    print("| Strike | CE Pre LTP | CE Post theoretical | CE Return % | PE Pre LTP | PE Post theoretical | PE Return % |")
    print("|---|---|---|---|---|---|---|")
    for strike in sorted(pre_data.keys()):
        row = sim_results[strike]
        ce_ret_pct = f"{row['ce_Scenario B: Spot Up 2.0%_return'] * 100:.2f}%"
        pe_ret_pct = f"{row['pe_Scenario B: Spot Up 2.0%_return'] * 100:.2f}%"
        print(f"| {strike} | {row['ce_pre_ltp']:.2f} | {row['ce_Scenario B: Spot Up 2.0%_price']:.2f} | **{ce_ret_pct}** | {row['pe_pre_ltp']:.2f} | {row['pe_Scenario B: Spot Up 2.0%_price']:.2f} | {pe_ret_pct} |")
        
    # Print comparison table for Scenario A (Spot Unchanged - Neutral)
    print("\n--- SIMULATION RESULTS: Scenario A (Spot Unchanged at 1296.40, IV Crushes to 15.0%) ---")
    print("| Strike | CE Pre LTP | CE Post theoretical | CE Return % | PE Pre LTP | PE Post theoretical | PE Return % |")
    print("|---|---|---|---|---|---|---|")
    for strike in sorted(pre_data.keys()):
        row = sim_results[strike]
        ce_ret_pct = f"{row['ce_Scenario A: Spot Unchanged_return'] * 100:.2f}%"
        pe_ret_pct = f"{row['pe_Scenario A: Spot Unchanged_return'] * 100:.2f}%"
        print(f"| {strike} | {row['ce_pre_ltp']:.2f} | {row['ce_Scenario A: Spot Unchanged_price']:.2f} | **{ce_ret_pct}** | {row['pe_pre_ltp']:.2f} | {row['pe_Scenario A: Spot Unchanged_price']:.2f} | {pe_ret_pct} |")
        
    # Save simulation results to CSV
    headers = ["strike", "ce_pre_ltp", "pe_pre_ltp", "ce_pre_iv", "pe_pre_iv"]
    for sc in scenarios:
        name = sc["name"]
        headers.extend([f"ce_{name}_price", f"ce_{name}_return", f"pe_{name}_price", f"pe_{name}_return"])
        
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for strike in sorted(sim_results.keys()):
            row = sim_results[strike]
            row_data = [strike, row["ce_pre_ltp"], row["pe_pre_ltp"], row["ce_pre_iv"], row["pe_pre_iv"]]
            for sc in scenarios:
                name = sc["name"]
                row_data.extend([
                    row[f"ce_{name}_price"], row[f"ce_{name}_return"],
                    row[f"pe_{name}_price"], row[f"pe_{name}_return"]
                ])
            writer.writerow(row_data)
            
    print(f"\nSimulation results saved to: {CSV_OUT}")
    return sim_results

def print_actual_comparison(pre_data, post_data, post_meta):
    print(f"\n--- ACTUAL POST-EVENT COMPARISON ---")
    print(f"Post-Event Snapshot Timestamp: {post_meta['timestamp']}")
    print(f"Post-Event Expiry:             {post_meta['expiry']}")
    print(f"Post-Event Spot Price:          {post_meta['spot']} (vs Pre-Event Spot: 1296.4)")
    print(f"Change in Spot:                 {post_meta['spot'] - 1296.4:.2f} ({((post_meta['spot'] - 1296.4) / 1296.4) * 100:.2f}%)")
    
    print("\n| Strike | CE Pre LTP | CE Post LTP | CE Change % | CE Pre IV | CE Post IV | PE Pre LTP | PE Post LTP | PE Change % | PE Pre IV | PE Post IV |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    
    comparison_rows = []
    
    for strike in sorted(pre_data.keys()):
        pre = pre_data[strike]
        post = post_data.get(strike, {"ce_ltp": 0.0, "pe_ltp": 0.0, "ce_iv": 0.0, "pe_iv": 0.0})
        
        ce_change = (post["ce_ltp"] - pre["ce_ltp"]) / pre["ce_ltp"] if pre["ce_ltp"] > 0 else 0.0
        pe_change = (post["pe_ltp"] - pre["pe_ltp"]) / pre["pe_ltp"] if pre["pe_ltp"] > 0 else 0.0
        
        print(f"| {strike} | {pre['ce_ltp']:.2f} | {post['ce_ltp']:.2f} | **{ce_change*100:.2f}%** | {pre['ce_iv']:.2f}% | {post['ce_iv']:.2f}% | {pre['pe_ltp']:.2f} | {post['pe_ltp']:.2f} | **{pe_change*100:.2f}%** | {pre['pe_iv']:.2f}% | {post['pe_iv']:.2f}% |")
        
        comparison_rows.append({
            "strike": strike,
            "ce_pre_ltp": pre["ce_ltp"], "ce_post_ltp": post["ce_ltp"], "ce_change": ce_change,
            "ce_pre_iv": pre["ce_iv"], "ce_post_iv": post["ce_iv"],
            "pe_pre_ltp": pre["pe_ltp"], "pe_post_ltp": post["pe_ltp"], "pe_change": pe_change,
            "pe_pre_iv": pre["pe_iv"], "pe_post_iv": post["pe_iv"]
        })
        
    # Save to CSV
    headers = [
        "strike", "ce_pre_ltp", "ce_post_ltp", "ce_change", "ce_pre_iv", "ce_post_iv",
        "pe_pre_ltp", "pe_post_ltp", "pe_change", "pe_pre_iv", "pe_post_iv"
    ]
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(comparison_rows)
        
    print(f"\nActual comparison saved to: {CSV_OUT}")

def main():
    print("=== RELIANCE BEFORE/AFTER COMPARISON LAYER ===")
    pre_data = load_pre_event_snapshot()
    post_data, post_meta = query_post_event_data()
    
    if post_data:
        print_actual_comparison(pre_data, post_data, post_meta)
    else:
        run_simulation(pre_data)

if __name__ == "__main__":
    main()
