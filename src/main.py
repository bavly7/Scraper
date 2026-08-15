import os
import time
import json
import requests
import re
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field, ValidationError

# Base configuration
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
BOOK_CACHE_DIR = CACHE_DIR / "books"
BOOK_CACHE_DIR.mkdir(exist_ok=True)

# Output directory for Stage 4
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Polite robot headers
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/bavly7/Scraper)"
}
REQUEST_TIMEOUT_SECONDS = 5
DELAY_SECONDS = 0.5


# --- PYDANTIC SCHEMA (Stage 4) ---
class BookRecord(BaseModel):
    title: str
    product_url: str = Field(pattern=r"^https://") # URL must start with https://
    price_text: str
    price_gbp: float
    availability_text: Optional[str] = None
    rating_text: Optional[str] = None
    description: Optional[str] = None
    source_page: str
    fetched_at: str


def fetch_and_cache(url: str, cache_path: Path) -> tuple[str, bool]:
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8"), True

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
    soup = BeautifulSoup(html, "html.parser")
    product_main = soup.select_one("article.product_page")
    
    title_tag = product_main.select_one("h1")
    title = title_tag.text if title_tag else None
    
    price_tag = product_main.select_one("p.price_color")
    price_text = price_tag.text if price_tag else None
    
    availability_tag = product_main.select_one("p.instock.availability")
    availability_text = availability_tag.text.strip() if availability_tag else None
    
    rating_tag = product_main.select_one("p.star-rating")
    rating_text = None
    if rating_tag:
        classes = rating_tag.attrs.get("class", [])
        if len(classes) > 1:
            rating_text = classes[1]
            
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
    return url.replace("https://books.toscrape.com/catalogue/", "").replace("/", "_")


def extract_price_gbp(price_text: str) -> float:
    """Extracts numeric value from a price string like '£51.77'."""
    if not price_text:
        return 0.0
    # Search for numbers and a dot
    match = re.search(r'[\d\.]+', price_text)
    if match:
        return float(match.group())
    return 0.0


def run_pipeline():
    print("--- Starting Pipeline ---")
    current_url = START_URL
    catalogue_pages_visited = 0
    discovered_records = []
    
    # --- STAGE 2: Discover ---
    while current_url and catalogue_pages_visited < 3:
        page_num = catalogue_pages_visited + 1
        cache_path = CACHE_DIR / f"catalogue-page-{page_num}.html"
        
        html, was_cached = fetch_and_cache(current_url, cache_path)
        if not was_cached:
            time.sleep(DELAY_SECONDS)
            
        links, next_url = parse_catalogue_page(html, current_url)
        for link in links:
            discovered_records.append({"book_url": link, "source_page": current_url})
            
        catalogue_pages_visited += 1
        current_url = next_url
        
    unique_records = {record["book_url"]: record for record in discovered_records}.values()
    
    # --- STAGE 3: Extract ---
    raw_books = []
    print(f"Extracting {len(unique_records)} books...")
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

    # --- STAGE 4: Clean, Validate, Store ---
    valid_books = {}
    errors = []
    
    for raw in raw_books:
        # 1. Normalize price
        price_text = raw.get("price_text")
        raw["price_gbp"] = extract_price_gbp(price_text)
        
        # 2. Schema Validation
        try:
            validated_book = BookRecord(**raw)
            # Use URL as dictionary key to enforce Idempotency (prevent duplicates)
            valid_books[validated_book.product_url] = validated_book.model_dump()
        except ValidationError as e:
            errors.append({
                "url": raw.get("product_url"),
                "reason": str(e)
            })
            
    # 3. Save to output/books.json
    books_file_path = OUTPUT_DIR / "books.json"
    with open(books_file_path, "w", encoding="utf-8") as f:
        json.dump(list(valid_books.values()), f, indent=2, ensure_ascii=False)
        
    # 4. Save to output/errors.json
    errors_file_path = OUTPUT_DIR / "errors.json"
    with open(errors_file_path, "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)

    # Checkpoint output
    print("\n--- CHECKPOINT RESULTS (STAGE 4) ---")
    print(f"Valid records in books.json: {len(valid_books)}")
    print(f"Invalid records in errors.json: {len(errors)}")

if __name__ == "__main__":
    run_pipeline()