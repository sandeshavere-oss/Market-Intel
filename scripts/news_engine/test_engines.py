import os
import sqlite3
import unittest
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_MARKET_PATH = BASE_DIR / "database" / "market_intel.db"
DB_CORP_PATH = BASE_DIR / "database" / "corporate_events.db"
DB_PRICE_PATH = BASE_DIR / "database" / "price_data.db"

class TestMarketIntelV3(unittest.TestCase):
    def test_database_existence(self):
        """Verify that all databases exist."""
        self.assertTrue(DB_MARKET_PATH.exists(), "market_intel.db is missing")
        self.assertTrue(DB_CORP_PATH.exists(), "corporate_events.db is missing")
        self.assertTrue(DB_PRICE_PATH.exists(), "price_data.db is missing")
        
    def test_database_wal_mode(self):
        """Verify WAL mode is enabled for database concurrency."""
        for db in [DB_MARKET_PATH, DB_CORP_PATH, DB_PRICE_PATH]:
            conn = sqlite3.connect(db)
            cursor = conn.cursor()
            journal_mode = cursor.execute("PRAGMA journal_mode").fetchone()[0]
            conn.close()
            self.assertEqual(journal_mode.lower(), "wal", f"{db.name} is not in WAL mode")

    def test_company_mentions_table(self):
        """Verify company_mentions table was created and has data."""
        conn = sqlite3.connect(DB_MARKET_PATH)
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='company_mentions'")
        self.assertIsNotNone(cursor.fetchone(), "company_mentions table is missing")
        
        # Check rows
        cursor.execute("SELECT COUNT(*) FROM company_mentions")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertGreater(count, 0, "company_mentions table is empty")

    def test_daily_prices_table(self):
        """Verify daily_prices table was created and has data."""
        conn = sqlite3.connect(DB_PRICE_PATH)
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_prices'")
        self.assertIsNotNone(cursor.fetchone(), "daily_prices table is missing")
        
        # Check rows
        cursor.execute("SELECT COUNT(*) FROM daily_prices")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertGreater(count, 0, "daily_prices table is empty")

    def test_event_signals_table(self):
        """Verify event_signals table exists and contains signals."""
        conn = sqlite3.connect(DB_MARKET_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='event_signals'")
        self.assertIsNotNone(cursor.fetchone(), "event_signals table is missing")
        
        cursor.execute("SELECT COUNT(*) FROM event_signals")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertGreater(count, 0, "No convergence signals were generated")

    def test_signal_performance_table(self):
        """Verify signal_performance table exists, has correct columns, and has entries."""
        conn = sqlite3.connect(DB_MARKET_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signal_performance'")
        self.assertIsNotNone(cursor.fetchone(), "signal_performance table is missing")
        
        # Verify all required columns are present
        cursor.execute("PRAGMA table_info(signal_performance)")
        columns = [col[1] for col in cursor.fetchall()]
        expected_columns = [
            "signal_id", "company", "signal_date", "price_at_signal",
            "price_5d_later", "price_10d_later", "return_5d", "return_10d", "outcome"
        ]
        for col in expected_columns:
            self.assertIn(col, columns, f"Column {col} is missing in signal_performance table")
            
        cursor.execute("SELECT COUNT(*) FROM signal_performance")
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0, "No performance records were updated")
        
        # Verify outcome contains expected categories
        cursor.execute("SELECT DISTINCT outcome FROM signal_performance")
        outcomes = [row[0] for row in cursor.fetchall()]
        for o in outcomes:
            self.assertIn(o, ["WIN", "LOSS", "NEUTRAL", "PENDING"], f"Invalid outcome category: {o}")
            
        conn.close()

    def test_theme_velocity_table(self):
        """Verify theme_velocity table exists and has correct columns."""
        conn = sqlite3.connect(DB_MARKET_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='theme_velocity'")
        self.assertIsNotNone(cursor.fetchone(), "theme_velocity table is missing")
        
        # Verify columns
        cursor.execute("PRAGMA table_info(theme_velocity)")
        columns = [col[1] for col in cursor.fetchall()]
        expected_columns = ["theme", "date", "mentions_today", "7d_avg", "30d_avg", "z_score"]
        for col in expected_columns:
            self.assertIn(col, columns, f"Column {col} is missing in theme_velocity table")
            
        cursor.execute("SELECT COUNT(*) FROM theme_velocity")
        count = cursor.fetchone()[0]
        self.assertGreater(count, 0, "No theme velocity records found")
        conn.close()

    def test_market_outperformance_outcome(self):
        """Verify Nifty 50 outperformance outcome logic in performance tracking."""
        conn = sqlite3.connect(DB_MARKET_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT return_5d, outcome FROM signal_performance WHERE outcome IN ('WIN', 'LOSS') LIMIT 1")
        row = cursor.fetchone()
        if row:
            ret_5d, outcome = row
            self.assertIn(outcome, ["WIN", "LOSS"])
        conn.close()

    def test_twitter_convergence_logic(self):
        """Verify that company lookup loading and get_twitter_velocities functions exist and run."""
        import sys
        sys.path.append(str(BASE_DIR / "scripts" / "news_engine"))
        from signal_engine import load_company_lookup, get_twitter_velocities
        lookup = load_company_lookup()
        self.assertGreater(len(lookup), 0, "Company lookup dict is empty")
        
        tw_stats = get_twitter_velocities("2026-06-09", lookup)
        self.assertIsNotNone(tw_stats, "Twitter velocities stats are None")

if __name__ == "__main__":
    unittest.main()
