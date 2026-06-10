import sqlite3
import csv
import sys
from pathlib import Path

# Resolve paths dynamically
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "DATABASE" / "market_intel.db"
MASTER_FILE = BASE_DIR / "MAPPINGS" / "company_master.csv"

def get_company_details(query: str) -> list[dict]:
    """
    Search company_master.csv for matching companies and return their details.
    """
    query = query.strip().lower()
    matches = []
    
    if not MASTER_FILE.exists():
        print(f"WARNING: Master company file not found at {MASTER_FILE}", file=sys.stderr)
        return matches

    try:
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("company_name", "").strip()
                symbol = row.get("symbol", "").strip()
                sector = row.get("sector", "").strip()
                aliases_raw = row.get("aliases", "").strip()
                
                # Split aliases by pipe
                aliases = [a.strip() for a in aliases_raw.split("|") if a.strip()]
                
                # Check if query matches name, symbol, or any alias
                match_found = False
                if query in name.lower() or query in symbol.lower():
                    match_found = True
                else:
                    for alias in aliases:
                        if query in alias.lower():
                            match_found = True
                            break
                            
                if match_found:
                    matches.append({
                        "name": name,
                        "symbol": symbol,
                        "sector": sector,
                        "aliases": aliases
                    })
    except Exception as e:
        print(f"Error reading company master: {e}", file=sys.stderr)
        
    return matches

def search_news_by_company(company_query: str) -> list[dict]:
    """
    Find matching companies and search for their news in the database.
    """
    results = []
    matching_companies = get_company_details(company_query)
    
    if not matching_companies:
        return results
        
    if not DB_PATH.exists():
        print(f"WARNING: Database file not found at {DB_PATH}", file=sys.stderr)
        return results
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # We want to match any article that lists the company name in its 'related_companies'
    # or mentions the company symbol/aliases in its title/keywords/raw_text
    all_articles = []
    seen_ids = set()
    
    for comp in matching_companies:
        name = comp["name"]
        symbol = comp["symbol"]
        aliases = comp["aliases"]
        
        # Build SQL condition
        # 1. Match name in related_companies
        conditions = ["related_companies LIKE ?"]
        params = [f"%{name}%"]
        
        # 2. Match symbol or aliases in title or keywords
        for alias in [name, symbol] + aliases:
            conditions.append("title LIKE ?")
            params.append(f"%{alias}%")
            conditions.append("keywords LIKE ?")
            params.append(f"%{alias}%")
            
        sql_query = f"""
            SELECT id, title, keywords, related_companies, theme, source, created_at, link 
            FROM keywords 
            WHERE {" OR ".join(conditions)}
            ORDER BY id DESC
        """
        
        try:
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()
            for r in rows:
                art_id = r[0]
                if art_id not in seen_ids:
                    seen_ids.add(art_id)
                    all_articles.append({
                        "id": r[0],
                        "title": r[1],
                        "keywords": r[2],
                        "related_companies": r[3],
                        "theme": r[4],
                        "source": r[5],
                        "created_at": r[6],
                        "link": r[7],
                        "matched_company": name,
                        "symbol": symbol,
                        "sector": comp["sector"]
                    })
        except Exception as e:
            print(f"Error querying database: {e}", file=sys.stderr)
            
    conn.close()
    return all_articles

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        print("Usage: python company_match.py <company_name_or_symbol>")
        sys.exit(1)
        
    query = sys.argv[1]
    print(f"Searching for news related to: '{query}'...")
    
    companies = get_company_details(query)
    if not companies:
        print("No matching companies found in master list.")
        sys.exit(0)
        
    print(f"Found {len(companies)} matching company entries:")
    for c in companies:
        print(f" - {c['name']} ({c['symbol']}) [{c['sector']}]")
        
    articles = search_news_by_company(query)
    print(f"\nFound {len(articles)} matching articles in database:")
    print("="*80)
    for idx, art in enumerate(articles, 1):
        print(f"{idx}. {art['title']}")
        print(f"   Date:      {art['created_at']} | Source: {art['source']}")
        print(f"   Theme:     {art['theme']} | Co: {art['related_companies']}")
        print(f"   Keywords:  {art['keywords']}")
        print(f"   Link:      {art['link']}")
        print("-"*80)

if __name__ == "__main__":
    main()
