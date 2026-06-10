import os
import json
from pathlib import Path

# Resolve paths
COOKIES_DIR = Path(__file__).resolve().parent
RAW_PATH = COOKIES_DIR / "raw_cookies.json"
TARGET_PATH = COOKIES_DIR / "twitter_cookies.json"

def convert_cookies():
    if not RAW_PATH.exists():
        print(f"Error: Raw cookies file not found at {RAW_PATH}")
        print("Please export your cookies from x.com as JSON, rename the file to 'raw_cookies.json', and save it inside SOCIAL_ENGINE/")
        return
        
    try:
        with open(RAW_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
        # Standard extensions export cookies as a list of dicts
        if not isinstance(raw_data, list):
            print("Error: Expected a JSON array/list of cookies in raw_cookies.json")
            return
            
        formatted_cookies = []
        for cookie in raw_data:
            # Map standard fields and clean up types
            name = cookie.get("name")
            value = cookie.get("value")
            domain = cookie.get("domain", ".x.com")
            path = cookie.get("path", "/")
            
            # Expires could be string or missing, handle safely
            expires = cookie.get("expirationDate") or cookie.get("expires")
            if expires is not None:
                try:
                    expires = float(expires)
                except ValueError:
                    expires = -1.0
            else:
                expires = -1.0
                
            http_only = bool(cookie.get("httpOnly", False))
            secure = bool(cookie.get("secure", True))
            
            # Map sameSite safely
            same_site = cookie.get("sameSite", "Lax")
            if same_site not in ["Lax", "None", "Strict"]:
                same_site = "Lax"
                
            formatted_cookies.append({
                "name": str(name),
                "value": str(value),
                "domain": str(domain),
                "path": str(path),
                "expires": expires,
                "httpOnly": http_only,
                "secure": secure,
                "sameSite": same_site
            })
            
        # Format as Playwright storage state structure
        storage_state = {
            "cookies": formatted_cookies,
            "origins": []
        }
        
        with open(TARGET_PATH, "w", encoding="utf-8") as f:
            json.dump(storage_state, f, indent=2)
            
        print(f"Success! Converted {len(formatted_cookies)} cookies.")
        print(f"Playwright cookies saved to: {TARGET_PATH}")
        print("You can now run the headless fetcher script: python SOCIAL_ENGINE/fetch_tweets.py")
        
    except Exception as e:
        print(f"Conversion failed: {e}")

if __name__ == "__main__":
    convert_cookies()
