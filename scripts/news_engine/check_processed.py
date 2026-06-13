import sys
import sqlite3
import json
from pathlib import Path

def main():
    # Try to parse base64 payload if a single arg is provided
    base64_payload = None
    if len(sys.argv) == 2:
        try:
            import base64
            decoded = base64.b64decode(sys.argv[1].encode('utf-8')).decode('utf-8')
            base64_payload = json.loads(decoded)
        except Exception as e:
            print(json.dumps({"error": f"Failed to decode base64 argument: {e}", "count": 0}))
            sys.exit(1)

    if base64_payload is not None:
        article_id = base64_payload.get("article_id", "")
        title = base64_payload.get("title", "")
        content = base64_payload.get("content", "")
        link = base64_payload.get("link", "")
        source_feed = base64_payload.get("source_feed", "")
        published_at = base64_payload.get("published_at", "")
    else:
        if len(sys.argv) < 7:
            print(json.dumps({"error": "Missing arguments", "count": 0}))
            sys.exit(1)

        article_id = sys.argv[1]
        title = sys.argv[2]
        content = sys.argv[3]
        link = sys.argv[4]
        source_feed = sys.argv[5]
        published_at = sys.argv[6]

    # Resolve database path dynamically
    base_dir = Path(__file__).resolve().parent.parent.parent
    db_path = base_dir / "DATABASE" / "market_intel.db"
    
    # Fallback to lowercase if uppercase doesn't exist (though they map to same on Windows)
    if not db_path.exists():
        db_path = base_dir / "database" / "market_intel.db"

    count = 0
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path), timeout=30)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM corporate_events WHERE article_id = ?", (article_id,))
            count = cursor.fetchone()[0]
            conn.close()
        except Exception as e:
            # Output error to stderr so n8n can capture it in logs, but return count=0 to stdout
            print(f"Error querying database: {e}", file=sys.stderr)
            count = 0
    else:
        print(f"Database path not found: {db_path}", file=sys.stderr)

    result = {
        "article_id": article_id,
        "title": title,
        "content": content,
        "link": link,
        "source_feed": source_feed,
        "published_at": published_at,
        "count": count
    }
    print(json.dumps(result))

if __name__ == "__main__":
    main()
