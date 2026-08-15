import time
import json
import requests
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import datetime, timezone

# Base configuration
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Sub-directory for book pages to keep things organized
BOOK_CACHE_DIR = CACHE_DIR / "books"
BOOK_CACHE_DIR.mkdir(exist_ok=True)

# Polite robot headers
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/bavly7/Scraper)"
}
REQUEST_TIMEOUT_SECONDS = 5
DELAY_SECONDS = 0.5


def fetch_and_cache(url: str, cache_path: Path) -> tuple[str, bool]:
    """Fetches a URL with caching and polite rules."""
    if cache_path.exists():
        content = cache_path.read_text(encoding="utf-8")
        return content, True

    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch {url}: Status code {response.status_code}")
            
        html_content = response.text
        cache_path.write_text(html_content, encoding="utf-8")
        return html_content, False

    except requests.RequestException as e:
        print(f"ERROR fetching {url}: {e}")
        raise


def parse_catalogue_page(html: str, page_url: str):
    """Extracts book URLs and the 'next' page URL."""
    soup = BeautifulSoup(html, "html.parser")
    book_links = []
    
    for article in soup.select("article.product_pod"):
        a_tag = article.select_one("h3 a")
        if a_tag and "href" in a_tag.attrs:
            absolute_url = urljoin(page_url, a_tag["href"])
            book_links.append(absolute_url)
            
    next_url = None
    next_button = soup.select_one("li.next a")
    if next_button and "href" in next_button.attrs:
        next_url = urljoin(page_url, next_button["href"])
        
    return book_links, next_url


def parse_book_page(html: str, product_url: str, source_page: str) -> dict:
    """Extracts the 8 raw fields from a single book page."""
    soup = BeautifulSoup(html, "html.parser")
    # Aiming selectors at the product area, not the whole document
    product_main = soup.select_one("article.product_page")
    
    # 1. Title
    title_tag = product_main.select_one("h1")
    title = title_tag.text if title_tag else None
    
    # 2. Price
    price_tag = product_main.select_one("p.price_color")
    price_text = price_tag.text if price_tag else None
    
    # 3. Availability
    availability_tag = product_main.select_one("p.instock.availability")
    availability_text = availability_tag.text.strip() if availability_tag else None
    
    # 4. Rating (Extracting class name like 'Three')
    rating_tag = product_main.select_one("p.star-rating")
    rating_text = None
    if rating_tag:
        classes = rating_tag.attrs.get("class", [])
        if len(classes) > 1:
            rating_text = classes[1]  # e.g., 'Three', 'One'
            
    # 5. Description (Handling missing descriptions with None/null)
    desc_header = product_main.select_one("#product_description")
    description = None
    if desc_header:
        desc_tag = desc_header.find_next_sibling("p")
        if desc_tag:
            description = desc_tag.text
            
    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }


def get_safe_filename(url: str) -> str:
    """Converts a URL into a safe filename for caching."""
    return url.replace("https://books.toscrape.com/catalogue/", "").replace("/", "_")


def run_stage_3():
    print("--- Running Stage 2 & 3 ---")
    current_url = START_URL
    catalogue_pages_visited = 0
    discovered_records = []
    
    # --- STAGE 2: Discover Links ---
    while current_url and catalogue_pages_visited < 3:
        page_num = catalogue_pages_visited + 1
        cache_path = CACHE_DIR / f"catalogue-page-{page_num}.html"
        
        html, was_cached = fetch_and_cache(current_url, cache_path)
        if not was_cached:
            time.sleep(DELAY_SECONDS)
            
        links, next_url = parse_catalogue_page(html, current_url)
        
        # We need to save the source_page along with the URL for Stage 3
        for link in links:
            discovered_records.append({"book_url": link, "source_page": current_url})
            
        catalogue_pages_visited += 1
        current_url = next_url
        
    # Remove duplicates based on URL
    unique_records = {record["book_url"]: record for record in discovered_records}.values()
    
    # --- STAGE 3: Extract Book Details ---
    raw_books = []
    
    print(f"Starting extraction for {len(unique_records)} books...")
    for idx, record in enumerate(unique_records):
        book_url = record["book_url"]
        source_page = record["source_page"]
        
        safe_name = get_safe_filename(book_url)
        cache_path = BOOK_CACHE_DIR / f"{safe_name}.html"
        
        html, was_cached = fetch_and_cache(book_url, cache_path)
        if not was_cached:
            time.sleep(DELAY_SECONDS)
            
        book_data = parse_book_page(html, book_url, source_page)
        raw_books.append(book_data)
        
        # Simple progress indicator
        if (idx + 1) % 10 == 0:
            print(f"Processed {idx + 1} / {len(unique_records)} books...")

    # Checkpoint verification
    print("\n--- CHECKPOINT RESULTS ---")
    # Print the very first complete raw record as JSON
    print(json.dumps(raw_books[0], indent=2, ensure_ascii=False))
    # Print the exact summary format requested
    print(f"\ndetail_pages={len(raw_books)}")

if __name__ == "__main__":
    run_stage_3()