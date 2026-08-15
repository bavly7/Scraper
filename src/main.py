import time
import json
import requests
import re
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, ValidationError

# Base configuration
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
BOOK_CACHE_DIR = CACHE_DIR / "books"
BOOK_CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/bavly7/Scraper)"}
REQUEST_TIMEOUT_SECONDS = 5
DELAY_SECONDS = 0.5

class BookRecord(BaseModel):
    title: str
    product_url: str = Field(pattern=r"^https://")
    price_text: str
    price_gbp: float
    availability_text: Optional[str] = None
    rating_text: Optional[str] = None
    description: Optional[str] = None
    source_page: str
    fetched_at: str

def get_safe_filename(url: str) -> str:
    return url.replace("https://books.toscrape.com/catalogue/", "").replace("/", "_")

def extract_price_gbp(price_text: str) -> float:
    if not price_text: return 0.0
    match = re.search(r'[\d\.]+', price_text)
    return float(match.group()) if match else 0.0

# --- UPDATED FETCH FUNCTION (STAGE 5 RETRY LOGIC) ---
def fetch_with_retry(url: str, headers: dict) -> Optional[str]:
    """Fetches a URL with 1 retry for timeouts/5xx. Returns HTML or None if failed."""
    for attempt in range(2): # Attempt 0, then Retry 1
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code == 200:
                return response.text
            elif response.status_code in (403, 404):
                print(f"  -> Skipping {url} (Status: {response.status_code})")
                return None # Do not retry 403 or 404
            elif response.status_code >= 500:
                print(f"  -> Server error {response.status_code}. Retrying...")
                time.sleep(2)
                continue
            else:
                return None
        except requests.exceptions.Timeout:
            print(f"  -> Timeout. Retrying...")
            time.sleep(2)
            continue
        except requests.exceptions.RequestException as e:
            print(f"  -> Request failed: {e}")
            return None
    return None

def fetch_and_cache(url: str, cache_path: Path, metrics: dict) -> tuple[Optional[str], bool]:
    if cache_path.exists():
        metrics["cache_hits"] += 1
        return cache_path.read_text(encoding="utf-8"), True

    metrics["pages_fetched"] += 1
    html_content = fetch_with_retry(url, HEADERS)
    
    if html_content:
        cache_path.write_text(html_content, encoding="utf-8")
        return html_content, False
    else:
        metrics["failed_pages"] += 1
        return None, False

def parse_catalogue_page(html: str, page_url: str):
    soup = BeautifulSoup(html, "html.parser")
    book_links = []
    for article in soup.select("article.product_pod"):
        a_tag = article.select_one("h3 a")
        if a_tag and "href" in a_tag.attrs:
            book_links.append(urljoin(page_url, a_tag["href"]))
    next_button = soup.select_one("li.next a")
    next_url = urljoin(page_url, next_button["href"]) if next_button and "href" in next_button.attrs else None
    return book_links, next_url

def parse_book_page(html: str, product_url: str, source_page: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    product_main = soup.select_one("article.product_page")
    
    title_tag = product_main.select_one("h1")
    title = title_tag.text if title_tag else None
    
    price_tag = product_main.select_one("p.price_color")
    price_text = price_tag.text if price_tag else None
    
    availability_tag = product_main.select_one("p.instock.availability")
    availability_text = availability_tag.text.strip() if availability_tag else None
    
    rating_tag = product_main.select_one("p.star-rating")
    rating_text = rating_tag.attrs.get("class", [])[1] if rating_tag and len(rating_tag.attrs.get("class", [])) > 1 else None
            
    desc_header = product_main.select_one("#product_description")
    description = desc_header.find_next_sibling("p").text if desc_header and desc_header.find_next_sibling("p") else None
            
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

def run_pipeline():
    # Setup Metrics Dictionary
    start_time_obj = datetime.now(timezone.utc)
    metrics = {
        "start_time": start_time_obj.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": 0.0,
        "pages_fetched": 0,
        "cache_hits": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "failed_pages": 0
    }
    
    print("--- Starting Pipeline ---")
    current_url = START_URL
    catalogue_pages_visited = 0
    discovered_records = []
    
    # --- STAGE 2: Discover ---
    while current_url and catalogue_pages_visited < 3:
        page_num = catalogue_pages_visited + 1
        cache_path = CACHE_DIR / f"catalogue-page-{page_num}.html"
        
        html, was_cached = fetch_and_cache(current_url, cache_path, metrics)
        if not html: break
        if not was_cached: time.sleep(DELAY_SECONDS)
            
        links, next_url = parse_catalogue_page(html, current_url)
        for link in links:
            discovered_records.append({"book_url": link, "source_page": current_url})
            
        catalogue_pages_visited += 1
        current_url = next_url
        
    unique_records = list({record["book_url"]: record for record in discovered_records}.values())
    
    # --- STAGE 5 INJECTION: Add a deliberate fake URL ---
    unique_records.append({
        "book_url": "https://books.toscrape.com/catalogue/this-is-a-fake-book-for-testing/index.html",
        "source_page": "manual_test"
    })
    print(f"\nAdded 1 fake URL for Stage 5 testing. Total URLs to process: {len(unique_records)}")

    # --- STAGE 3: Extract ---
    raw_books = []
    for idx, record in enumerate(unique_records):
        book_url = record["book_url"]
        source_page = record["source_page"]
        
        safe_name = get_safe_filename(book_url)
        cache_path = BOOK_CACHE_DIR / f"{safe_name}.html"
        
        html, was_cached = fetch_and_cache(book_url, cache_path, metrics)
        
        # If the page failed to fetch, just skip extraction and continue loop
        if not html:
            continue
            
        if not was_cached: time.sleep(DELAY_SECONDS)
            
        book_data = parse_book_page(html, book_url, source_page)
        raw_books.append(book_data)

    # --- STAGE 4: Clean, Validate, Store ---
    valid_books = {}
    errors = []
    
    for raw in raw_books:
        raw["price_gbp"] = extract_price_gbp(raw.get("price_text"))
        try:
            validated_book = BookRecord(**raw)
            valid_books[validated_book.product_url] = validated_book.model_dump()
            metrics["valid_records"] += 1
        except ValidationError as e:
            errors.append({"url": raw.get("product_url"), "reason": str(e)})
            metrics["invalid_records"] += 1
            
    with open(OUTPUT_DIR / "books.json", "w", encoding="utf-8") as f:
        json.dump(list(valid_books.values()), f, indent=2, ensure_ascii=False)
        
    with open(OUTPUT_DIR / "errors.json", "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)

    # --- STAGE 5: Finalize Metrics & Report ---
    end_time_obj = datetime.now(timezone.utc)
    metrics["duration_seconds"] = round((end_time_obj - start_time_obj).total_seconds(), 2)
    
    with open(OUTPUT_DIR / "run-report.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print("\n--- CHECKPOINT RESULTS (STAGE 5) ---")
    print(f"Valid records in books.json: {len(valid_books)}")
    print(f"Failed pages in run-report.json: {metrics['failed_pages']}")

if __name__ == "__main__":
    run_pipeline()