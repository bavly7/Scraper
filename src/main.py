import os
import requests
from pathlib import Path

# Base configuration
BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Polite robot headers
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/your-username/scraper)"
}
REQUEST_TIMEOUT_SECONDS = 5


def fetch_and_cache(url: str, cache_path: Path) -> str:
    """
    Politely fetches a URL with caching, custom User-Agent, timeout, and status verification.
    """
    # 1. Check if the page is already cached locally
    if cache_path.exists():
        content = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT | Size: {len(content.encode('utf-8'))} bytes | File: {cache_path.name}")
        return content

    # 2. Fetch directly from the network if not cached
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        
        # Verify status code is strictly 200 OK
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch {url}: Status code {response.status_code}")
            
        html_content = response.text
        
        # 3. Save to cache
        cache_path.write_text(html_content, encoding="utf-8")
        print(f"FETCH     | Size: {len(response.content)} bytes | Status: {response.status_code}")
        return html_content

    except requests.RequestException as e:
        print(f"ERROR fetching {url}: {e}")
        raise


if __name__ == "__main__":
    target_cache_file = CACHE_DIR / "catalogue-page-1.html"
    print("--- Running Stage 1 ---")
    fetch_and_cache(BASE_URL, target_cache_file)