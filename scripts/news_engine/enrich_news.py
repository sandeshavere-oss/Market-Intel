import sqlite3
import json
import logging
import urllib.request
import urllib.error
import sys
import re
import csv
from datetime import datetime
from pathlib import Path

# The 16 frozen themes allowed in theme_mapping.csv
FROZEN_THEMES = {
    "AI", "Semiconductor", "Banking", "Capital Markets", "Energy", "Defence", "Pharma",
    "Digital Infrastructure", "Green Energy", "Telecom", "Space Economy", "Macro Economy",
    "Commodities", "Metals & Mining", "EV", "Technology"
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

def enforce_theme_rules(themes_list):
    approved_themes = set()
    backlog_path = BASE_DIR / "data" / "mappings" / "theme_backlog.csv"
    
    # Read existing backlog keywords to avoid duplicates
    existing_backlog_keys = set()
    if backlog_path.exists():
        try:
            with open(backlog_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None) # skip header
                for row in reader:
                    if row:
                        existing_backlog_keys.add(row[0].strip().lower())
        except Exception:
            pass

    new_backlog_entries = []
    
    for theme in themes_list:
        t_clean = theme.strip()
        if not t_clean:
            continue
        t_lower = t_clean.lower()
        
        # 1. Standardize
        standardized = None
        if t_clean in FROZEN_THEMES:
            standardized = t_clean
        elif t_lower in THEME_STANDARDIZATION:
            standardized = THEME_STANDARDIZATION[t_lower]
        
        if standardized:
            approved_themes.add(standardized)
        else:
            # Add to backlog
            if t_lower not in existing_backlog_keys:
                new_backlog_entries.append([t_clean, t_clean])
                existing_backlog_keys.add(t_lower)
                
    # Append to backlog.csv
    if new_backlog_entries:
        try:
            write_header = not backlog_path.exists()
            with open(backlog_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(["keyword", "suggested_theme"])
                writer.writerows(new_backlog_entries)
                logger.info(f"Added {len(new_backlog_entries)} themes to theme backlog.")
        except Exception as e:
            logger.error(f"Failed to append to theme backlog: {e}")
            
    return list(approved_themes)

# Setup Logging via shared module
sys.path.append(str(Path(__file__).resolve().parent))
from logger_setup import get_logger
logger = get_logger("enrich_news.py")

# Resolve Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "database" / "market_intel.db"
OLLAMA_URL = "http://localhost:11434/api/generate"

def query_ollama_enrichment(title, raw_text):
    """Queries local Ollama (Mistral 7B) to extract keywords, companies, and themes."""
    prompt = f"""Analyze this financial article to extract key keywords, companies, and themes.

Title: {title}
Content: {raw_text[:3000]}

Return EXACTLY a JSON block with keys:
{{
  "keywords": "comma-separated list of key entities or subjects",
  "companies": ["company1", "company2"] or [],
  "themes": ["theme1", "theme2"] or []
}}

Rules:
- Output ONLY the JSON block. Do not include markdown blocks (like ```json) or any other text.
"""
    payload = {
        "model": "mistral:7b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 150,
            "num_ctx": 2048
        }
    }
    
    try:
        req = urllib.request.Request(
            OLLAMA_URL, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=240) as response:
            result = json.loads(response.read().decode('utf-8'))
            raw_response = result.get("response", "").strip()
            
            # Clean up potential markdown formatting
            raw_response = re.sub(r"^```json\s*", "", raw_response)
            raw_response = re.sub(r"\s*```$", "", raw_response)
            raw_response = raw_response.strip()
            
            # Find the JSON block boundaries if LLM outputs extra text
            start = raw_response.find('{')
            end = raw_response.rfind('}') + 1
            if start != -1 and end != 0:
                raw_response = raw_response[start:end]
                
            data = json.loads(raw_response)
            return {
                "keywords": data.get("keywords", "").strip(),
                "companies": [c.strip() for c in data.get("companies", []) if c.strip()],
                "themes": [t.strip() for t in data.get("themes", []) if t.strip()]
            }
    except Exception as e:
        logger.error(f"Failed to query Ollama for article '{title}': {e}")
        return None

def process_difficult_articles(conn):
    """Selects and enriches difficult articles using Ollama."""
    cursor = conn.cursor()
    
    # Query up to 10 unprocessed difficult articles
    cursor.execute("""
        SELECT id, title, raw_text, related_companies, theme, keywords
        FROM keywords
        WHERE processed = 0
          AND (company_match_count = 0 OR theme_match_count = 0)
          AND length(raw_text) > 150
        LIMIT 10
    """)
    rows = cursor.fetchall()
    
    if not rows:
        logger.info("No difficult articles in the queue.")
        return 0
        
    logger.info(f"Found {len(rows)} difficult articles to enrich using Ollama.")
    processed_count = 0
    
    for row in rows:
        art_id, title, raw_text, existing_cos, existing_themes, existing_kws = row
        logger.info(f"Enriching article ID {art_id}: '{title}'...")
        
        # Query Ollama
        enrichment = query_ollama_enrichment(title, raw_text)
        
        # Parse current values
        cos_set = set(c.strip() for c in existing_cos.split("|") if c.strip())
        themes_set = set(t.strip() for t in existing_themes.split("|") if t.strip())
        kws_set = set(k.strip() for k in existing_kws.split(",") if k.strip())
        
        if enrichment:
            # Merge companies
            for c in enrichment["companies"]:
                cos_set.add(c)
            # Merge themes
            for t in enrichment["themes"]:
                themes_set.add(t)
            # Merge keywords
            new_kws = [k.strip() for k in enrichment["keywords"].split(",") if k.strip()]
            for k in new_kws:
                kws_set.add(k)
                
            logger.info(f"Article ID {art_id} enriched. Companies added: {enrichment['companies']}, Themes added: {enrichment['themes']}")
        else:
            logger.warning(f"Skipping LLM updates for article ID {art_id} due to API failure.")

        # Update record in DB
        related_companies = "|".join(sorted(list(cos_set)))
        
        # Enforce theme mapping rules and log to backlog if emerging
        approved_themes = enforce_theme_rules(list(themes_set))
        theme = "|".join(sorted(approved_themes))
        
        keywords = ", ".join(sorted(list(kws_set)))
        
        # Update record in DB, keeping source_timestamp and system_timestamp untouched to maintain backward compatibility
        cursor.execute(
            """
            UPDATE keywords
            SET keywords = ?,
                related_companies = ?,
                theme = ?,
                company_match_count = ?,
                theme_match_count = ?,
                processed = 1,
                enriched_at = ?
            WHERE id = ?
            """,
            (
                keywords,
                related_companies,
                theme,
                len(cos_set),
                len(approved_themes),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                art_id
            )
        )
        processed_count += 1
        
    conn.commit()
    return processed_count

def process_easy_articles(conn):
    """Processes easy articles directly in bulk, bypassing Ollama."""
    cursor = conn.cursor()
    
    # Query all articles that are processed = 0 but are easy (they don't meet difficult criteria)
    # i.e., (company_match_count > 0 AND theme_match_count > 0) OR length(raw_text) <= 150
    cursor.execute("""
        SELECT id, title
        FROM keywords
        WHERE processed = 0
          AND NOT (
            (company_match_count = 0 OR theme_match_count = 0)
            AND length(raw_text) > 150
          )
    """)
    rows = cursor.fetchall()
    
    if not rows:
        logger.info("No easy articles in the queue.")
        return 0
        
    logger.info(f"Found {len(rows)} easy articles to mark as processed.")
    
    for row in rows:
        art_id, title = row
        cursor.execute(
            """
            UPDATE keywords
            SET processed = 1,
                enriched_at = ?
            WHERE id = ?
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                art_id
            )
        )
        
    conn.commit()
    logger.info(f"Successfully processed {len(rows)} easy articles in bulk.")
    return len(rows)

def main():
    if not DB_PATH.exists():
        logger.error(f"Database file not found at {DB_PATH}. Exiting.")
        sys.exit(1)
        
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        difficult_processed = process_difficult_articles(conn)
        easy_processed = process_easy_articles(conn)
        total_processed = difficult_processed + easy_processed
        
        # Log warnings if no articles were found to enrich
        if total_processed == 0:
            logger.warning("No unprocessed articles found in the queue.")
        else:
            logger.info(f"Enrichment task completed. Total difficult: {difficult_processed}, Total easy: {easy_processed}.")
            
        return total_processed
    except Exception as e:
        logger.critical(f"Enrichment task crashed: {e}", exc_info=True)
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Script started")
    try:
        processed_count = main()
        logger.info(f"Completed. {processed_count} articles processed")
    except Exception as e:
        logger.error(f"FATAL: {str(e)}", exc_info=True)
        sys.exit(1)
