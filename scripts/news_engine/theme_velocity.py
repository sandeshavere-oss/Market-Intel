import os
import sqlite3
import math
from pathlib import Path
from datetime import datetime, timedelta

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "market_intel.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "theme_velocity.log"

# Ensure directories exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_message(level, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} [{level}] {msg}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

# The 16 frozen themes
FROZEN_THEMES = [
    "AI", "Semiconductor", "Banking", "Capital Markets", "Energy", "Defence", "Pharma",
    "Digital Infrastructure", "Green Energy", "Telecom", "Space Economy", "Macro Economy",
    "Commodities", "Metals & Mining", "EV", "Technology"
]

def init_db():
    log_message("INFO", f"Initializing theme_velocity table in: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS theme_velocity (
            theme TEXT,
            date TEXT,
            mentions_today INTEGER,
            "7d_avg" REAL,
            "30d_avg" REAL,
            z_score REAL,
            PRIMARY KEY (theme, date)
        )
    """)
    conn.commit()
    conn.close()

def calculate_theme_velocity():
    init_db()
    
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    cursor = conn.cursor()
    
    # 1. Fetch all processed articles and their themes
    cursor.execute("""
        SELECT theme, created_at 
        FROM keywords 
        WHERE processed = 1
    """)
    rows = cursor.fetchall()
    
    if not rows:
        log_message("WARNING", "No processed articles found to calculate theme velocity.")
        conn.close()
        return
        
    # Aggregate mentions count: {(theme, date_str): count}
    mention_counts = {}
    
    min_date = None
    max_date = None
    
    for row in rows:
        theme_str, created_at = row
        if not created_at or not theme_str:
            continue
            
        try:
            date_str = created_at.split()[0]
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            continue
            
        if min_date is None or dt < min_date:
            min_date = dt
        if max_date is None or dt > max_date:
            max_date = dt
            
        themes = [t.strip() for t in theme_str.split("|") if t.strip()]
        for t in themes:
            if t in FROZEN_THEMES:
                mention_counts[(t, date_str)] = mention_counts.get((t, date_str), 0) + 1
                
    if not min_date or not max_date:
        log_message("WARNING", "No valid dates found in keywords.")
        conn.close()
        return
        
    # Standardize end date to today to ensure rolling averages are updated up to today
    today_dt = datetime.now()
    if today_dt > max_date:
        max_date = today_dt
        
    # Generate full list of dates between min_date and max_date
    date_list = []
    curr = min_date
    while curr <= max_date:
        date_list.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
        
    log_message("INFO", f"Calculating theme velocity from {date_list[0]} to {date_list[-1]} ({len(date_list)} days).")
    
    insert_rows = []
    
    for theme in FROZEN_THEMES:
        # Build complete daily series of mentions for this theme
        series = []
        for d_str in date_list:
            count = mention_counts.get((theme, d_str), 0)
            series.append((d_str, count))
            
        # Compute rolling stats for each day
        for idx in range(len(series)):
            d_str, val_today = series[idx]
            
            # Preceding 7-day window (idx - 7 to idx - 1)
            window_7 = [series[i][1] for i in range(max(0, idx - 7), idx)]
            avg_7 = sum(window_7) / len(window_7) if window_7 else 0.0
            
            # Preceding 30-day window (idx - 30 to idx - 1)
            window_30 = [series[i][1] for i in range(max(0, idx - 30), idx)]
            avg_30 = sum(window_30) / len(window_30) if window_30 else 0.0
            
            # Calculate standard deviation of preceding 30 days
            if window_30:
                variance = sum((x - avg_30) ** 2 for x in window_30) / len(window_30)
                std_dev = math.sqrt(variance)
            else:
                std_dev = 0.0
                
            # Z-score: (val_today - avg_30) / std_dev
            if std_dev > 0.0:
                z_score = (val_today - avg_30) / std_dev
            else:
                z_score = 0.0
                
            insert_rows.append((theme, d_str, val_today, avg_7, avg_30, z_score))
            
    # Write to database
    cursor.executemany("""
        INSERT OR REPLACE INTO theme_velocity (theme, date, mentions_today, "7d_avg", "30d_avg", z_score)
        VALUES (?, ?, ?, ?, ?, ?)
    """, insert_rows)
    
    conn.commit()
    conn.close()
    log_message("INFO", f"Successfully updated theme velocity for {len(insert_rows)} records.")

if __name__ == "__main__":
    calculate_theme_velocity()
