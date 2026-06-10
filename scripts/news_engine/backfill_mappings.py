import sqlite3
import csv
import sys
from pathlib import Path

# Resolve paths dynamically
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "market_intel.db"
MAPPING_FILE = BASE_DIR / "data" / "mappings" / "company_mapping.csv"
THEME_FILE = BASE_DIR / "data" / "mappings" / "theme_mapping.csv"

def load_company_mappings():
    mappings = []
    try:
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("keyword") and row.get("companies"):
                    mappings.append({
                        "keyword": row["keyword"].strip().lower(),
                        "companies": row["companies"].strip()
                    })
    except Exception as e:
        print(f"Error loading company mappings: {e}", file=sys.stderr)
    return mappings

def load_theme_mappings():
    mappings = []
    try:
        with open(THEME_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("keyword") and row.get("theme"):
                    mappings.append({
                        "keyword": row["keyword"].strip().lower(),
                        "theme": row["theme"].strip()
                    })
    except Exception as e:
        print(f"Error loading theme mappings: {e}", file=sys.stderr)
    return mappings

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("Starting database backfill...")
    print(f"DB Path: {DB_PATH}")
    print(f"Mapping Path: {MAPPING_FILE}")
    print(f"Theme Path: {THEME_FILE}")
    
    if not DB_PATH.exists():
        print(f"ERROR: Database file does not exist at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
        
    company_rules = load_company_mappings()
    theme_rules = load_theme_mappings()
    
    print(f"Loaded {len(company_rules)} company mapping rules.")
    print(f"Loaded {len(theme_rules)} theme mapping rules.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query all rows in the keywords table
    cursor.execute("SELECT id, title, keywords, related_companies, theme FROM keywords")
    rows = cursor.fetchall()
    print(f"Total rows fetched: {len(rows)}")
    
    updated_count = 0
    
    for row_id, title, keywords_str, old_companies, old_theme in rows:
        # Check if they are empty
        if not keywords_str:
            continue
            
        keyword_list = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
        
        # 1. Match related companies
        companies_matched = []
        for rule in company_rules:
            if rule["keyword"] in keyword_list:
                companies_matched.append(rule["companies"])
        companies_matched = sorted(list(set(companies_matched)))
        new_companies = "|".join(companies_matched)
        
        # 2. Match themes
        themes_matched = []
        for rule in theme_rules:
            if rule["keyword"] in keyword_list:
                themes_matched.append(rule["theme"])
        themes_matched = sorted(list(set(themes_matched)))
        new_theme = "|".join(themes_matched)
        
        # Update if changed or empty
        # We update if they are different from what is stored (e.g. they were empty but now have values)
        if new_companies != old_companies or new_theme != old_theme:
            cursor.execute(
                """
                UPDATE keywords
                SET related_companies = ?, theme = ?
                WHERE id = ?
                """,
                (new_companies, new_theme, row_id)
            )
            updated_count += 1
            
    conn.commit()
    conn.close()
    
    print("="*60)
    print("BACKFILL COMPLETED SUCCESSFULLY")
    print(f"Total rows processed: {len(rows)}")
    print(f"Total rows updated:   {updated_count}")
    print("="*60)

if __name__ == "__main__":
    main()
