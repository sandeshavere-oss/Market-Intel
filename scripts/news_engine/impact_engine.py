import os
import sys
import sqlite3
import math
from datetime import datetime
from pathlib import Path

# Resolve base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_MARKET_PATH = BASE_DIR / "database" / "market_intel.db"
DB_PRICE_PATH = BASE_DIR / "database" / "price_data.db"

# Ensure directories exist
DB_MARKET_PATH.parent.mkdir(parents=True, exist_ok=True)

# Reconfigure stdout to use UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

class ImpactEngine:
    def __init__(self):
        self.db_market = DB_MARKET_PATH
        self.db_price = DB_PRICE_PATH

    def get_options_data(self, symbol, date_str):
        """Queries options summary and nearest expiry chain data for a symbol on/before date_str."""
        if not self.db_price.exists():
            return None
            
        conn = sqlite3.connect(self.db_price)
        cursor = conn.cursor()
        
        try:
            # 1. Fetch latest options summary on or before date_str
            cursor.execute("""
                SELECT pcr, underlying_price, snapshot_timestamp
                FROM options_summary
                WHERE symbol = ? AND date(snapshot_timestamp) <= ?
                ORDER BY snapshot_timestamp DESC
                LIMIT 1
            """, (symbol, date_str))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
                
            pcr, spot_price, snapshot_ts = row
            
            # 2. Get nearest expiry date for this snapshot
            cursor.execute("""
                SELECT MIN(expiry)
                FROM options_chain
                WHERE symbol = ? AND snapshot_timestamp = ?
            """, (symbol, snapshot_ts))
            expiry_row = cursor.fetchone()
            if not expiry_row or not expiry_row[0]:
                conn.close()
                return {"pcr": pcr, "implied_volatility": 0.0, "iv_percentile": None}
                
            nearest_expiry = expiry_row[0]
            
            # 3. Fetch ATM CE and PE rows (closest to spot price)
            cursor.execute("""
                SELECT implied_volatility, iv_percentile
                FROM options_chain
                WHERE symbol = ? AND snapshot_timestamp = ? AND expiry = ?
                ORDER BY ABS(strike - ?) ASC
                LIMIT 2
            """, (symbol, snapshot_ts, nearest_expiry, spot_price))
            
            atm_rows = cursor.fetchall()
            
            iv_sum = 0.0
            iv_count = 0
            iv_percentile = None
            
            for iv, ivp in atm_rows:
                if iv and iv > 0.0:
                    iv_sum += iv
                    iv_count += 1
                    if ivp is not None:
                        iv_percentile = ivp
                        
            avg_iv = iv_sum / iv_count if iv_count > 0 else 0.0
            conn.close()
            
            return {
                "pcr": pcr,
                "implied_volatility": avg_iv,
                "iv_percentile": iv_percentile
            }
        except Exception as e:
            if conn:
                conn.close()
            return None

    def get_theme_z_score(self, theme, date_str):
        """Queries the theme velocity table for the Z-score of a theme."""
        conn = sqlite3.connect(self.db_market)
        cursor = conn.cursor()
        z_score = 0.0
        try:
            cursor.execute("""
                SELECT z_score 
                FROM theme_velocity 
                WHERE theme = ? AND date <= ?
                ORDER BY date DESC
                LIMIT 1
            """, (theme, date_str))
            row = cursor.fetchone()
            if row and row[0] is not None:
                z_score = row[0]
        except Exception:
            pass
        finally:
            conn.close()
        return z_score

    def get_node_by_name(self, node_name):
        conn = sqlite3.connect(self.db_market)
        cursor = conn.cursor()
        cursor.execute("SELECT id, node_name, node_type, symbol FROM graph_nodes WHERE node_name = ?", (node_name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {"id": row[0], "name": row[1], "type": row[2], "symbol": row[3]}
        return None

    def query_outgoing_edges(self, node_id):
        conn = sqlite3.connect(self.db_market)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.target_node_id, n.node_name, n.node_type, n.symbol, e.relationship_type, e.weight
            FROM graph_edges e
            JOIN graph_nodes n ON e.target_node_id = n.id
            WHERE e.source_node_id = ?
        """, (node_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{
            "id": r[0], "name": r[1], "type": r[2], "symbol": r[3], "rel_type": r[4], "weight": r[5]
        } for r in rows]

    def traverse_graph(self, start_node, initial_dir, expectation_changed, max_depth=4):
        """
        Traverses the Knowledge Graph recursively up to max_depth.
        Returns a list of impacted company nodes with computed path multipliers and directions.
        """
        impacted_companies = []
        
        # Helper DFS function
        def dfs(curr_node, curr_depth, path_multiplier, curr_dir, visited):
            # Cap depth
            if curr_depth > max_depth:
                return
                
            # If it's a listed company, add to results (leaf nodes in our queries)
            if curr_node["type"] == "Company" and curr_node["symbol"]:
                impacted_companies.append({
                    "node": curr_node,
                    "depth": curr_depth,
                    "multiplier": path_multiplier,
                    "direction": curr_dir
                })
                # We can still continue if there are further links, but usually companies are leaves
                
            # Query outgoing edges
            edges = self.query_outgoing_edges(curr_node["id"])
            
            # Decay factor: Depth 1 = 1.0, Depth 2 = 0.5, Depth 3 = 0.25, Depth 4 = 0.125
            decay_factor = 1.0 if curr_depth == 0 else (0.5 ** (curr_depth - 1))
            
            for edge in edges:
                tgt_id = edge["id"]
                if tgt_id in visited:
                    continue
                    
                # Determine weight
                edge_weight = edge["weight"]
                next_multiplier = path_multiplier * edge_weight * decay_factor
                
                # Determine direction propagation (flipping logic)
                next_dir = curr_dir
                rel_type = edge["rel_type"]
                
                # Negative relationships flip direction
                if rel_type in ("HURTS", "COMPETITOR_OF"):
                    next_dir = "BEARISH" if curr_dir == "BULLISH" else "BULLISH"
                elif rel_type == "INPUT_OF":
                    # If the source node represents a rising cost (BULLISH price shock), 
                    # traversing INPUT_OF to its user flips direction to BEARISH (higher costs hurt margins).
                    # If the source represents falling costs (BEARISH price shock), it makes user BULLISH (margins expand).
                    # For Supply shocks, direction (e.g. BEARISH = supply drops) does NOT flip when traversing INPUT_OF.
                    if expectation_changed in ("Pricing", "Cost", "Raw Material Cost"):
                        next_dir = "BEARISH" if curr_dir == "BULLISH" else "BULLISH"

                
                # Recursive call
                new_visited = visited.copy()
                new_visited.add(tgt_id)
                
                tgt_node = {"id": edge["id"], "name": edge["name"], "type": edge["type"], "symbol": edge["symbol"]}
                dfs(tgt_node, curr_depth + 1, next_multiplier, next_dir, new_visited)

        # Start traversal
        start_node_info = self.get_node_by_name(start_node)
        if not start_node_info:
            print(f"Error: Node '{start_node}' not found in Knowledge Graph.")
            return []
            
        dfs(start_node_info, 0, 1.0, initial_dir, {start_node_info["id"]})
        return impacted_companies


    def process_impact_event(self, article_title, source, event_type, expectation_changed, 
                             first_order_node, initial_direction, raw_magnitude, 
                             initial_conviction, signal_date, signal_horizon, related_theme=None):
        """
        Runs the full impact propagation, scoring, options validation, and database storage.
        """
        print(f"\n=========================================")
        print(f"Ingesting Event Article: '{article_title}'")
        print(f"Event Type: {event_type} | Changed Expectation: {expectation_changed}")
        print(f"First-Order Node: '{first_order_node}' ({initial_direction})")
        print(f"=========================================")
        
        # 1. Traverse Graph to find all downstream listed companies
        propagation_results = self.traverse_graph(first_order_node, initial_direction, expectation_changed)
        
        if not propagation_results:
            print("No downstream listed Indian companies impacted by this event path.")
            return []
            
        # Deduplicate results: if a company is reached via multiple paths, keep the highest multiplier path
        deduped_results = {}
        for res in propagation_results:
            sym = res["node"]["symbol"]
            if sym not in deduped_results or res["multiplier"] > deduped_results[sym]["multiplier"]:
                deduped_results[sym] = res
                
        signals_generated = []
        
        conn_market = sqlite3.connect(self.db_market)
        cursor_market = conn_market.cursor()
        
        for sym, res in deduped_results.items():
            comp_name = res["node"]["name"]
            depth = res["depth"]
            multiplier = res["multiplier"]
            direction = res["direction"]
            
            # 2. Conviction Scoring Model
            # Source Quality score
            src_score = 40.0
            if source.lower() in ("bse", "disclosure", "bse notice"):
                src_score = 100.0
            elif source.lower() in ("reuters", "bloomberg", "wsj"):
                src_score = 85.0
            elif source.lower() in ("moneycontrol", "cnbc", "economic times", "rss"):
                src_score = 70.0
                
            # Theme validation (Z-score from theme velocity)
            theme_score = 50.0
            if related_theme:
                z_score = self.get_theme_z_score(related_theme, signal_date)
                theme_score = min(max((z_score / 4.0) * 100.0, 0.0), 100.0)
                
            # Base conviction
            base_conviction = (0.30 * src_score) + (0.30 * initial_conviction) + (0.40 * theme_score)
            
            # Options layer penalty check
            pcr_level = None
            iv_percentile = None
            options_penalty = 0.0
            
            options_data = self.get_options_data(comp_name, signal_date)
            if options_data:
                pcr_level = options_data["pcr"]
                iv_percentile = options_data["iv_percentile"]
                iv_abs = options_data["implied_volatility"]
                
                # Fallback for IV percentile
                effective_iv_pct = iv_percentile
                if effective_iv_pct is None and iv_abs > 0.0:
                    effective_iv_pct = min(max((iv_abs / 30.0) * 100.0, 0.0), 100.0)
                    
                if effective_iv_pct is not None and effective_iv_pct > 80.0:
                    options_penalty = min(max((effective_iv_pct - 80.0) / 20.0, 0.0), 1.0) * 15.0
                    
            final_conviction = max(base_conviction - options_penalty, 0.0)
            
            # Compute Magnitude Score (decays with depth)
            magnitude = raw_magnitude * multiplier
            
            # Expected Alpha Score (EAS) for ranking
            eas_score = round(final_conviction * (magnitude / 100.0), 2)
            
            # Map EAS score back to ranking tiers
            if eas_score > 60.0:
                tier = "Tier 1 (High Conviction)"
            elif eas_score >= 45.0:
                tier = "Tier 2 (Medium Conviction)"
            elif eas_score >= 30.0:
                tier = "Tier 3 (Swing Conviction)"
            else:
                tier = "Tier 4 (Discarded/Monitor)"
                
            print(f"🎯 Propagation Node: **{comp_name}** ({sym})")
            print(f"  - Depth Level: {depth}-Order Effect")
            print(f"  - Traversal Multiplier: {multiplier:.4f}")
            print(f"  - Implied Direction: {direction}")
            print(f"  - Conviction Score: {final_conviction:.2f} (Options Penalty: -{options_penalty:.2f})")
            print(f"  - Expected Magnitude: {magnitude:.2f}%")
            print(f"  - Expected Alpha Score (EAS): {eas_score} -> **{tier}**")
            
            # 3. Save to database table impact_signals
            cursor_market.execute("""
                INSERT INTO impact_signals (
                    article_id, event_type, expectation_changed, first_order_node,
                    target_company, ticker, order_depth, direction, conviction_score,
                    magnitude_score, signal_horizon, pcr_level, iv_percentile, signal_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                1, event_type, expectation_changed, first_order_node,
                comp_name, sym, depth, direction, round(final_conviction, 2),
                round(magnitude, 2), signal_horizon, pcr_level, iv_percentile, signal_date
            ))
            
            signals_generated.append({
                "company": comp_name,
                "symbol": sym,
                "depth": depth,
                "direction": direction,
                "conviction": final_conviction,
                "magnitude": magnitude,
                "eas": eas_score,
                "tier": tier
            })
            
        conn_market.commit()
        conn_market.close()
        
        return signals_generated

if __name__ == "__main__":
    # Test script runs the engine on a dummy event
    engine = ImpactEngine()
    engine.process_impact_event(
        article_title="Geopolitical tensions block semiconductor shipping in Taiwan Strait",
        source="Reuters",
        event_type="Geopolitical",
        expectation_changed="Supply Shock",
        first_order_node="Taiwan Foundry Disruption",
        initial_direction="BULLISH",
        raw_magnitude=80.0,
        initial_conviction=90.0,
        signal_date="2026-06-12",
        signal_horizon="3 Month",
        related_theme="Semiconductors"
    )
