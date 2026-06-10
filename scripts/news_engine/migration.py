import sqlite3
import os
from pathlib import Path
import logging

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Resolve database path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "market_intel.db"

def run_migration():
    if not DB_PATH.exists():
        logger.error(f"Database file not found at: {DB_PATH}")
        return False
        
    logger.info(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()
    
    # Check current columns in keywords table
    cursor.execute("PRAGMA table_info(keywords)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # 1. Add source_timestamp if missing
    if "source_timestamp" not in columns:
        logger.info("Adding source_timestamp column to keywords table...")
        cursor.execute("ALTER TABLE keywords ADD COLUMN source_timestamp TEXT;")
        logger.info("source_timestamp column added successfully.")
    else:
        logger.info("source_timestamp column already exists in keywords table.")
        
    # 2. Add system_timestamp if missing
    if "system_timestamp" not in columns:
        logger.info("Adding system_timestamp column to keywords table...")
        cursor.execute("ALTER TABLE keywords ADD COLUMN system_timestamp TEXT;")
        logger.info("system_timestamp column added successfully.")
    else:
        logger.info("system_timestamp column already exists in keywords table.")
        
    conn.commit()
    conn.close()
    logger.info("Migration check completed successfully.")
    return True

if __name__ == "__main__":
    run_migration()
