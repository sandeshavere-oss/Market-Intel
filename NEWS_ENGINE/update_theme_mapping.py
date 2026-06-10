import csv
import os
from pathlib import Path

# Resolve base paths
BASE_DIR = Path(__file__).resolve().parent.parent
MAPPING_DIR = BASE_DIR / "MAPPINGS"
THEME_MAP_FILE = MAPPING_DIR / "theme_mapping.csv"
BACKLOG_FILE = MAPPING_DIR / "theme_backlog.csv"

# The 16 frozen themes allowed in theme_mapping.csv
FROZEN_THEMES = {
    "AI",
    "Semiconductor",
    "Banking",
    "Capital Markets",
    "Energy",
    "Defence",
    "Pharma",
    "Digital Infrastructure",
    "Green Energy",
    "Telecom",
    "Space Economy",
    "Macro Economy",
    "Commodities",
    "Metals & Mining",
    "EV",
    "Technology"
}

# Mapping rules to standardize theme names to the 16 frozen themes
THEME_STANDARDIZATION = {
    "artificial intelligence": "AI",
    "generative ai": "AI",
    "ai infrastructure": "AI",
    "semiconductors": "Semiconductor",
    "semiconductor manufacturing": "Semiconductor",
    "healthcare": "Pharma",
    "oil & gas": "Energy",
    "data center": "Digital Infrastructure",
    "datacenter": "Digital Infrastructure",
    "defense indigenization": "Defence",
    "drone ecosystem": "Defence",
    "fintech": "Capital Markets",
    "digital payments": "Banking",
    "nbfc": "Banking",
    "microfinance": "Banking",
    "satellites": "Space Economy",
    "stock market analysis": "Capital Markets",
    "financial performance": "Capital Markets",
}

# Standard mappings from keyword (lowercase) to frozen theme
STANDARD_MAPPINGS = {
    # AI
    "ai": "AI",
    "artificial intelligence": "AI",
    "machine learning": "AI",
    "deep learning": "AI",
    "llm": "AI",
    "chatgpt": "AI",
    "gemini": "AI",
    "claude": "AI",
    "generative ai": "AI",
    
    # EV
    "battery": "EV",
    "electric vehicle": "EV",
    "ev": "EV",
    "electric car": "EV",
    "charging station": "EV",
    "charging infrastructure": "EV",
    "lithium battery": "EV",
    "energy storage": "EV",
    
    # Digital Infrastructure
    "datacentre": "Digital Infrastructure",
    "data centre": "Digital Infrastructure",
    "datacenter": "Digital Infrastructure",
    "cloud computing": "Digital Infrastructure",
    "server": "Digital Infrastructure",
    "aws": "Digital Infrastructure",
    "azure": "Digital Infrastructure",
    "google cloud": "Digital Infrastructure",
    "hyperscaler": "Digital Infrastructure",
    
    # Semiconductor
    "semiconductor": "Semiconductor",
    "semiconductors": "Semiconductor",
    "chipmaker": "Semiconductor",
    "ai chipmakers": "Semiconductor",
    "chip": "Semiconductor",
    "wafer": "Semiconductor",
    "foundry": "Semiconductor",
    "nvidia": "Semiconductor",
    "amd": "Semiconductor",
    "intel": "Semiconductor",
    "semiconductor manufacturing": "Semiconductor",
}

def update_theme_mapping():
    if not THEME_MAP_FILE.exists():
        print(f"ERROR: File not found at {THEME_MAP_FILE}")
        return

    # Read existing CSV
    with open(THEME_MAP_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("ERROR: theme_mapping.csv is empty!")
        return

    header = rows[0]
    data_rows = rows[1:]

    # Detect column positions
    try:
        header_lower = [h.lower().strip() for h in header]
        keyword_col = header_lower.index("keyword")
        theme_col = header_lower.index("theme")
    except ValueError:
        # Fallback to check other column headers
        try:
            keyword_col = header_lower.index("raw_keyword")
            theme_col = header_lower.index("standard_theme")
        except ValueError:
            # Fallback to column index 0 and 1
            keyword_col = 0
            theme_col = 1

    approved_rows = []
    backlog_rows = []
    seen_keywords = set()

    for row in data_rows:
        if not row or len(row) <= max(keyword_col, theme_col):
            continue

        keyword = row[keyword_col].strip().lower()
        theme = row[theme_col].strip()

        # Handle duplicate keywords
        if keyword in seen_keywords:
            continue
        seen_keywords.add(keyword)

        # Standardize theme if mapping exists
        theme_lower = theme.lower()
        if theme_lower in THEME_STANDARDIZATION:
            theme = THEME_STANDARDIZATION[theme_lower]
        
        # Override with standard mappings if applicable
        if keyword in STANDARD_MAPPINGS:
            theme = STANDARD_MAPPINGS[keyword]

        # Verify against allowed themes
        if theme in FROZEN_THEMES:
            approved_rows.append([row[keyword_col].strip(), theme])
        else:
            backlog_rows.append([row[keyword_col].strip(), theme])

    # Add any missing standard mappings
    for keyword, theme in STANDARD_MAPPINGS.items():
        if keyword not in seen_keywords:
            approved_rows.append([keyword, theme])
            seen_keywords.add(keyword)

    # Save approved theme mappings back to theme_mapping.csv
    with open(THEME_MAP_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["keyword", "theme"])
        writer.writerows(approved_rows)

    # Save backlog mappings to theme_backlog.csv (Append if exists)
    write_backlog_header = not BACKLOG_FILE.exists()
    with open(BACKLOG_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if write_backlog_header:
            writer.writerow(["keyword", "suggested_theme"])
        writer.writerows(backlog_rows)

    # Summary
    print("\n" + "="*40)
    print("   THEME MAPPING FREEZE UPDATE SUMMARY")
    print("="*40)
    print(f"Total input rows read    : {len(data_rows)}")
    print(f"Approved themes saved    : {len(approved_rows)}")
    print(f"Backlog themes diverted   : {len(backlog_rows)}")
    print("="*40)
    print(f"theme_mapping.csv updated: {THEME_MAP_FILE}")
    print(f"theme_backlog.csv appended: {BACKLOG_FILE}")
    print("Done! [OK]")

if __name__ == "__main__":
    update_theme_mapping()
