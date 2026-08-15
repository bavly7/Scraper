import time
import requests
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Base configuration
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Polite robot headers
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/bavly7/Scraper)"
}
REQUEST_TIMEOUT_SECONDS = 5
DELAY_SECONDS = 0.5


def fetch_and_cache(url: str, cache_path: Path) -> tuple[str, bool]:
    """
    Fetches a URL. Returns the HTML content and a boolean indicating if it was a cache hit.
    """
    # 1. Check Cache
    if cache_path.exists():
        content = cache_path.read_text(encoding="utf-8")
        print(f"CACHE HIT | File: {cache_path.name}")
        return content, True

    # 2. Fetch from network
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch {url}: Status code {response.status_code}")
            
        html_content = response.text
        # 3. Save to Cache
        cache_path.write_text(html_content, encoding="utf-8")
        print(f"FETCH     | URL: {url}")
        return html_content, False

    except requests.RequestException as e:
        print(f"ERROR fetching {url}: {e}")
        raise


def parse_catalogue_page(html: str, page_url: str):
    """
    Extracts book URLs and the 'next' page URL from the HTML.
    """
    soup = BeautifulSoup(html, "html.parser")
    book_links = []
    
    # 1. Find all books (they are inside <article class="product_pod">)
    for article in soup.select("article.product_pod"):
        a_tag = article.select_one("h3 a")
        if a_tag and "href" in a_tag.attrs:
            # Turn relative URL into an absolute URL
            absolute_url = urljoin(page_url, a_tag["href"])
            book_links.append(absolute_url)
            
    # 2. Find 'next' page link
    next_url = None
    next_button = soup.select_one("li.next a")
    if next_button and "href" in next_button.attrs:
        next_url = urljoin(page_url, next_button["href"])
        
    return book_links, next_url


def run_stage_2():
    print("--- Running Stage 2: Discovering Book URLs ---")
    current_url = START_URL
    catalogue_pages_visited = 0
    discovered_urls = []
    
    # Stop after 3 pages or if there is no 'next' page
    while current_url and catalogue_pages_visited < 3:
        page_num = catalogue_pages_visited + 1
        cache_path = CACHE_DIR / f"catalogue-page-{page_num}.html"
        
        # Fetch the page
        html, was_cached = fetch_and_cache(current_url, cache_path)
        
        # Polite delay ONLY if it was a real request (not from cache)
        if not was_cached:
            time.sleep(DELAY_SECONDS)
            
        # Extract links
        links, next_url = parse_catalogue_page(html, current_url)
        discovered_urls.extend(links)
        
        catalogue_pages_visited += 1
        current_url = next_url
        
    # Remove duplicates by converting list to a set, then back to a list
    unique_urls = list(set(discovered_urls))
    
    # Print the exact checkpoint format required
    print(f"catalogue_pages={catalogue_pages_visited}, discovered={len(discovered_urls)}, unique_urls={len(unique_urls)}")


if __name__ == "__main__":
    run_stage_2()