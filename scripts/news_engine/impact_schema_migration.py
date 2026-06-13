import os
import sqlite3
import sys
from pathlib import Path

# Resolve base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "market_intel.db"

# Ensure directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Reconfigure stdout to use UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def init_impact_schema():
    print(f"Initializing Impact Propagation schemas in: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable WAL mode
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # 1. Create graph_nodes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graph_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_name TEXT UNIQUE NOT NULL,
            node_type TEXT NOT NULL,
            symbol TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # 2. Create graph_edges table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graph_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_node_id INTEGER,
            target_node_id INTEGER,
            relationship_type TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(source_node_id) REFERENCES graph_nodes(id) ON DELETE CASCADE,
            FOREIGN KEY(target_node_id) REFERENCES graph_nodes(id) ON DELETE CASCADE,
            UNIQUE(source_node_id, target_node_id, relationship_type)
        );
    """)
    
    # 3. Create indexes for graph traversal
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_node_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_node_id);")
    
    # 4. Create impact_signals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS impact_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            event_type TEXT NOT NULL,
            expectation_changed TEXT NOT NULL,
            first_order_node TEXT NOT NULL,
            target_company TEXT NOT NULL,
            ticker TEXT,
            order_depth INTEGER NOT NULL,
            direction TEXT NOT NULL,
            conviction_score REAL NOT NULL,
            magnitude_score REAL NOT NULL,
            signal_horizon TEXT NOT NULL,
            pcr_level REAL,
            iv_percentile REAL,
            signal_date TEXT NOT NULL,
            processed INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_impact_signals_company ON impact_signals(target_company);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_impact_signals_date ON impact_signals(signal_date);")
    
    conn.commit()
    print("Schema tables and indexes created successfully.")
    conn.close()

def seed_knowledge_graph():
    print("Seeding Knowledge Graph with baseline nodes and edges...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # List of baseline nodes
    nodes = [
        # 1. Anthropic AI Shutdown Scenario
        ("Anthropic Claude", "Technology", None),
        ("Google Gemini", "Technology", None),
        ("US Tech Firms", "Sector", None),
        ("Indian IT Exporters", "Sector", None),
        ("TCS", "Company", "TCS.NS"),
        ("INFY", "Company", "INFY.NS"),
        ("Indian Cloud Providers", "Sector", None),
        ("TATACOMM", "Company", "TATACOMM.NS"),
        
        # 2. Oil Shock Scenario
        ("Brent Crude", "Commodity", None),
        ("Petrochemicals", "Sector", None),
        ("Chemical Producers", "Sector", None),
        ("Paint Companies", "Sector", None),
        ("ASIANPAINT", "Company", "ASIANPAINT.NS"),
        ("National Oil Exploration", "Sector", None),
        ("ONGC", "Company", "ONGC.NS"),
        ("RELIANCE", "Company", "RELIANCE.NS"),
        
        # 3. Defense Order Scenario
        ("Indian Defense Allocation", "Regulation", None),
        ("Defense PSUs", "Sector", None),
        ("HAL", "Company", "HAL.NS"),
        ("Defense Electronics", "Sector", None),
        ("BEL", "Company", "BEL.NS"),
        
        # 4. Semiconductor Shortage Scenario
        ("Taiwan Foundry Disruption", "Geopolitical", None),
        ("Semiconductor Supply", "Supply Chain", None),
        ("Auto ECU Components", "Supply Chain", None),
        ("Auto Manufacturers", "Sector", None),
        ("TATAMOTORS", "Company", "TATAMOTORS.NS"),
        ("MARUTI", "Company", "MARUTI.NS"),
        ("Domestic Semiconductor Initiatives", "Theme", None),
        ("Semiconductor OSAT", "Sector", None),
        ("CGPOWER", "Company", "CGPOWER.NS"),
        
        # 5. Solid-State Battery Scenario
        ("Solid-State Battery", "Technology", None),
        ("Electric Vehicles", "Theme", None),
        ("Traditional Lithium-Ion", "Theme", None),
        ("Domestic Battery Suppliers", "Sector", None),
        ("EXIDEIND", "Company", "EXIDEIND.NS"),
        ("Legacy Battery Manufacturers", "Sector", None),
        ("AMARAJABAT", "Company", "AMARAJABAT.NS")
    ]
    
    # Insert Nodes
    cursor.executemany("""
        INSERT OR IGNORE INTO graph_nodes (node_name, node_type, symbol)
        VALUES (?, ?, ?)
    """, nodes)
    conn.commit()
    print(f"Nodes seeded. Total nodes in table: {cursor.execute('SELECT COUNT(*) FROM graph_nodes').fetchone()[0]}")
    
    # Load nodes to get their IDs
    cursor.execute("SELECT node_name, id FROM graph_nodes")
    node_id_map = {row[0]: row[1] for row in cursor.fetchall()}
    
    # List of directed edges: (source_name, target_name, rel_type, weight)
    edges = [
        # Anthropic AI Shutdown
        ("Anthropic Claude", "Google Gemini", "COMPETITOR_OF", 0.9),
        ("Anthropic Claude", "US Tech Firms", "INPUT_OF", 0.8),
        ("US Tech Firms", "Indian IT Exporters", "CLIENT_OF", 0.7),
        ("Indian IT Exporters", "TCS", "CONSTITUENT_OF", 0.5),
        ("Indian IT Exporters", "INFY", "CONSTITUENT_OF", 0.5),
        ("Google Gemini", "Indian Cloud Providers", "INPUT_OF", 0.7),
        ("Indian Cloud Providers", "TATACOMM", "CONSTITUENT_OF", 0.6),
        
        # Oil Shock
        ("Brent Crude", "Petrochemicals", "INPUT_OF", 0.9),
        ("Petrochemicals", "Chemical Producers", "INPUT_OF", 0.8),
        ("Chemical Producers", "Paint Companies", "INPUT_OF", 0.8),
        ("Paint Companies", "ASIANPAINT", "CONSTITUENT_OF", 0.9),
        ("Brent Crude", "National Oil Exploration", "BENEFITS", 0.8),
        ("National Oil Exploration", "ONGC", "CONSTITUENT_OF", 0.9),
        ("Petrochemicals", "RELIANCE", "CONSTITUENT_OF", 0.7),
        
        # Defense Allocation
        ("Indian Defense Allocation", "Defense PSUs", "BENEFITS", 0.95),
        ("Defense PSUs", "HAL", "CONSTITUENT_OF", 0.9),
        ("Indian Defense Allocation", "Defense Electronics", "BENEFITS", 0.9),
        ("Defense Electronics", "BEL", "CONSTITUENT_OF", 0.9),
        
        # Semiconductor Shortage
        ("Taiwan Foundry Disruption", "Semiconductor Supply", "HURTS", 0.9),
        ("Semiconductor Supply", "Auto ECU Components", "INPUT_OF", 0.85),
        ("Auto ECU Components", "Auto Manufacturers", "INPUT_OF", 0.8),
        ("Auto Manufacturers", "TATAMOTORS", "CONSTITUENT_OF", 0.5),
        ("Auto Manufacturers", "MARUTI", "CONSTITUENT_OF", 0.5),
        ("Taiwan Foundry Disruption", "Domestic Semiconductor Initiatives", "BENEFITS", 0.7),
        ("Domestic Semiconductor Initiatives", "Semiconductor OSAT", "INPUT_OF", 0.8),
        ("Semiconductor OSAT", "CGPOWER", "CONSTITUENT_OF", 0.9),
        
        # Solid-State Battery
        ("Solid-State Battery", "Electric Vehicles", "BENEFITS", 0.9),
        ("Solid-State Battery", "Traditional Lithium-Ion", "HURTS", 0.7),
        ("Electric Vehicles", "Domestic Battery Suppliers", "INPUT_OF", 0.8),
        ("Domestic Battery Suppliers", "EXIDEIND", "CONSTITUENT_OF", 0.9),
        ("Traditional Lithium-Ion", "Legacy Battery Manufacturers", "INPUT_OF", 0.8),
        ("Legacy Battery Manufacturers", "AMARAJABAT", "CONSTITUENT_OF", 0.9)
    ]
    
    # Prepare edge insert parameters
    edge_params = []
    for src, tgt, rel, wt in edges:
        src_id = node_id_map.get(src)
        tgt_id = node_id_map.get(tgt)
        if src_id and tgt_id:
            edge_params.append((src_id, tgt_id, rel, wt))
        else:
            print(f"Warning: Node name not found: '{src}' or '{tgt}'")
            
    cursor.executemany("""
        INSERT OR IGNORE INTO graph_edges (source_node_id, target_node_id, relationship_type, weight)
        VALUES (?, ?, ?, ?)
    """, edge_params)
    conn.commit()
    print(f"Edges seeded. Total edges in table: {cursor.execute('SELECT COUNT(*) FROM graph_edges').fetchone()[0]}")
    conn.close()

if __name__ == "__main__":
    init_impact_schema()
    seed_knowledge_graph()
    print("Database schema migration and seeding completed successfully.")
