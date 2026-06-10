import os
import sys
import json
import logging
import re
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
COOKIES_PATH = Path(__file__).resolve().parent / "twitter_cookies.json"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "twitter_engine.log"

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
# Add console logging to stderr to keep stdout clean for JSON piping
console = logging.StreamHandler(sys.stderr)
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)

def fetch_tweets(query=None):
    if not COOKIES_PATH.exists():
        logging.error(f"Cookies file not found at {COOKIES_PATH}. Ingestion aborted.")
        print(f"Error: Session cookies file not found at {COOKIES_PATH}", file=sys.stderr)
        print("Please log in to x.com on your desktop browser, export cookies as JSON to 'raw_cookies.json' inside SOCIAL_ENGINE/, and run 'python SOCIAL_ENGINE/convert_cookies.py' to generate the Playwright cookies.", file=sys.stderr)
        sys.exit(1)
        
    tweets = []
    
    with sync_playwright() as p:
        logging.info("Launching browser (Headless)...")
        browser = p.chromium.launch(headless=True)
        
        # Real browser User-Agent and viewport to bypass bot detection checks
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        context = browser.new_context(
            storage_state=str(COOKIES_PATH),
            user_agent=user_agent,
            viewport={"width": 1280, "height": 800}
        )
        logging.info("Loaded session cookies from disk.")
            
        page = context.new_page()
        
        # Navigate to home first to verify session is valid
        try:
            logging.info("Navigating to x.com/home to verify session validity...")
            page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            
            # Check if redirected to login page or if home timeline is blocked
            is_login = "login" in page.url or page.locator('input[autocomplete="username"]').is_visible()
            has_tweets = page.locator('article[data-testid="tweet"]').first.is_visible()
            
            if is_login or not has_tweets:
                logging.error("Session expired or invalid. Bypassing automation to avoid locks.")
                print("Error: Session expired or invalid. Please export fresh cookies from your browser.", file=sys.stderr)
                browser.close()
                sys.exit(1)
                
            logging.info("Session verified successfully.")
        except Exception as ex:
            logging.critical(f"Error checking session: {ex}", exc_info=True)
            print(f"Error checking session: {ex}", file=sys.stderr)
            browser.close()
            sys.exit(1)
            
        # Navigate to target page (search query or home feed)
        if query:
            target_url = f"https://x.com/search?q={re.escape(query)}&f=live"
            logging.info(f"Searching for tweets with query: '{query}'...")
        else:
            target_url = "https://x.com/home"
            logging.info("Fetching tweets from home timeline...")
            
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            
            # Scroll down to load more tweets
            logging.info("Scrolling down to load more tweets...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(3000)
            
            # Parse tweets
            tweet_elements = page.locator('article[data-testid="tweet"]').all()
            logging.info(f"Found {len(tweet_elements)} raw tweets on the page.")
            
            for elem in tweet_elements:
                try:
                    # 1. Extract tweet URL first
                    url_elem = elem.locator('a[href*="/status/"]').first
                    href = url_elem.get_attribute("href") if url_elem else ""
                    tweet_url = f"https://x.com{href}" if href else ""
                    
                    # 2. Extract twitter handle (robust URL parsing with DOM fallback)
                    handle = "unknown"
                    if tweet_url:
                        url_match = re.search(r'(?:x|twitter)\.com/([^/]+)/status/', tweet_url)
                        if url_match:
                            handle = url_match.group(1)
                            
                    if handle == "unknown":
                        handle_elem = elem.locator('div[data-testid="User-Name"] a').first
                        handle_text = handle_elem.text_content() if handle_elem else ""
                        handle_match = re.search(r'@(\w+)', handle_text)
                        if handle_match:
                            handle = handle_match.group(1)
                    
                    # 3. Extract tweet text
                    text_elem = elem.locator('div[data-testid="tweetText"]').first
                    tweet_text = text_elem.text_content() if text_elem else ""
                    
                    if tweet_text and tweet_url:
                        tweets.append({
                            "twitter_handle": handle,
                            "tweet_text": tweet_text.strip(),
                            "tweet_url": tweet_url,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                except Exception as e:
                    logging.debug(f"Error parsing single tweet element: {e}")
                    
            # Save updated cookies state to keep session active
            context.storage_state(path=str(COOKIES_PATH))
            logging.info("Refreshed session storage state on disk.")
        except Exception as ex:
            logging.error(f"Error during tweet fetching: {ex}", exc_info=True)
            print(f"Error during tweet fetching: {ex}", file=sys.stderr)
        finally:
            browser.close()
        
    logging.info(f"Fetcher completed. Parsed {len(tweets)} tweets.")
    return tweets

if __name__ == "__main__":
    query_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        results = fetch_tweets(query_arg)
        # Print JSON array to stdout for piping
        print(json.dumps(results, indent=2))
    except Exception as ex:
        logging.critical(f"Fetcher script crashed: {ex}", exc_info=True)
        print("[]")
        sys.exit(1)

