# The Polite Scraper

**FlyRank Internship — Week 5, Assignment A9**

A robust, polite Python web scraping pipeline that extracts **60 book records** from the [Books to Scrape](https://books.toscrape.com/) sandbox, normalizes prices, validates data using Pydantic, handles network failures gracefully, and outputs clean structured JSON with a full run report.

---

## 📌 Overview

The project demonstrates how to build a production-minded web scraper that focuses not only on extracting data, but also on:

* Respectful request handling
* Rate limiting
* Local caching
* Network failure handling
* Data validation
* Data normalization
* Provenance tracking
* Structured JSON output
* Run-level reporting

---

## 🛠️ Tech Stack

| Component             | Technology       |
| --------------------- | ---------------- |
| **Language**          | Python 3.10+     |
| **HTTP Requests**     | Requests         |
| **HTML Parser**       | Beautiful Soup 4 |
| **Schema Validation** | Pydantic         |
| **Output Format**     | JSON             |

---

## 🎯 Target Classification

### Target Site

**Books to Scrape**
https://books.toscrape.com/

Books to Scrape is a public practice sandbox specifically designed for learning and testing web scraping safely.

### Scope

The scraper processes exactly:

* **3 catalogue pages**
* **20 books per page**
* **60 unique books total**

### Data Collected

For each book, the pipeline extracts:

* Title
* Product URL
* Raw price
* Normalized price in GBP
* Availability
* Rating
* Description
* Source page provenance
* Fetch timestamp

### `robots.txt` Check

The scraper requested:

```text
https://books.toscrape.com/robots.txt
```

The server returned **404 — Not Found**.

A missing `robots.txt` file is treated as simply a missing file, **not as explicit permission to scrape**. The target site is, however, an open sandbox specifically intended for scraping practice.

> **Policy:** This code should not be reused against another website without checking that site's rules, terms, and scraping policies first.

---

# 🤝 Politeness Rules

The scraper follows several rules to minimize unnecessary load on the target server.

### 1. Custom User-Agent

The scraper identifies itself using a custom User-Agent:

```text
FlyRankInternship-A9/1.0 (+https://github.com/bavly7/Scraper)
```

This makes the requests identifiable rather than pretending to be a normal browser.

### 2. Rate Limiting

The pipeline waits at least:

```text
0.5 seconds
```

between real network requests.

This prevents sending requests too aggressively.

### 3. Request Timeouts

Every network request has a hard timeout of:

```text
5 seconds
```

This prevents the scraper from hanging indefinitely when a server becomes slow or unavailable.

### 4. Local Caching

Downloaded HTML pages are cached locally.

This means that during development or repeated runs, the scraper can reuse previously downloaded pages instead of repeatedly requesting the live server.

---

# 📦 Record Schema

Every extracted book record is validated using **Pydantic** before being stored.

The schema contains:

| Field               | Type     | Required | Description                                  |
| ------------------- | -------- | -------- | -------------------------------------------- |
| `title`             | `string` | ✅        | Book title                                   |
| `product_url`       | `string` | ✅        | Full HTTPS product URL                       |
| `price_text`        | `string` | ✅        | Original price extracted from the page       |
| `price_gbp`         | `float`  | ✅        | Normalized numeric price in GBP              |
| `availability_text` | `string` | ❌        | Availability information                     |
| `rating_text`       | `string` | ❌        | Rating information                           |
| `description`       | `string` | ❌        | Book description                             |
| `source_page`       | `string` | ✅        | Catalogue page where the book was discovered |
| `fetched_at`        | `string` | ✅        | ISO 8601 timestamp                           |

### Example Record

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_text": "£51.77",
  "price_gbp": 51.77,
  "availability_text": "In stock",
  "rating_text": "Three",
  "description": "It's hard to imagine...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-08-15T18:00:00Z"
}
```

---

# 🚀 How to Run in 5 Minutes

## 1. Clone the Repository

```bash
git clone https://github.com/bavly7/Scraper.git
cd Scraper
```

## 2. Create a Virtual Environment

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the Pipeline

```bash
python src/main.py
```

After execution, check:

```text
output/
├── books.json
├── errors.json
└── run-report.json
```

---

# 📊 Sample Run Report

The pipeline generates a `run-report.json` file containing information about the execution.

Example:

```json
{
  "start_time": "2026-08-15T18:00:00Z",
  "duration_seconds": 3.45,
  "pages_fetched": 4,
  "cache_hits": 60,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1
}
```

### Report Fields

| Field              | Description                                 |
| ------------------ | ------------------------------------------- |
| `start_time`       | Time when the pipeline started              |
| `duration_seconds` | Total execution time                        |
| `pages_fetched`    | Number of catalogue/product pages requested |
| `cache_hits`       | Number of pages served from local cache     |
| `valid_records`    | Records successfully validated              |
| `invalid_records`  | Records rejected by schema validation       |
| `failed_pages`     | Pages that failed during fetching           |

---

# 🧠 Why No Browser Was Needed

A headless browser such as **Playwright** or **Selenium** was not necessary for this project.

The target website is **server-rendered**, meaning the required book information is already available in the raw HTML returned by the server.

Therefore, using:

```text
Requests → Beautiful Soup → Pydantic
```

is sufficient.

Using a browser would introduce additional:

* Memory usage
* Startup time
* CPU overhead
* System complexity

without providing any structural benefit for this particular website.

### Architecture

```text
                 ┌────────────────────┐
                 │  Books to Scrape   │
                 └─────────┬──────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │     Requests    │
                  │  HTTP Fetching  │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Local Cache    │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  BeautifulSoup  │
                  │  HTML Parsing   │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Data Normalize   │
                  │ & Transform      │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │    Pydantic     │
                  │   Validation    │
                  └────────┬────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │       JSON Output        │
              ├──────────────────────────┤
              │ books.json               │
              │ errors.json              │
              │ run-report.json          │
              └──────────────────────────┘
```

---

# ⚠️ Limitations

The scraper is intentionally designed for **Books to Scrape**.

Its CSS selectors are tightly coupled to the current HTML structure of the website.

For example, if the website changes:

```html
<article class="product_pod">
```

to something like:

```html
<div class="book-item">
```

the existing selectors would need to be updated.

Therefore, the scraper should **not be considered a universal scraper**.

Before adapting it to another website, you should manually inspect the target site's:

* HTML structure
* URL patterns
* Pagination
* Robots.txt
* Terms of Service
* Rate limits
* Anti-bot mechanisms
* Data usage policies

---

# 📁 Project Outputs

After a successful run, the project produces:

```text
output/
│
├── books.json
│   └── Validated book records
│
├── errors.json
│   └── Failed requests and validation errors
│
└── run-report.json
    └── Pipeline execution statistics
```

---

# 🎓 Key Learning Outcomes

This assignment demonstrates practical knowledge of:

* Web scraping with Python
* HTML inspection and CSS selectors
* Relative vs. absolute URLs
* Pagination handling
* HTTP request management
* Rate limiting
* Local caching
* Error handling
* Data normalization
* Pydantic validation
* Data provenance
* Structured JSON output
* Pipeline execution reporting

---

# 🔑 Core Principle

> **A good scraper is not just a script that extracts data. It is a controlled pipeline that knows what to request, how often to request it, how to handle failures, how to validate the results, and where the data came from.**

The main workflow is:

```text
Inspect
   ↓
Understand the HTML
   ↓
Discover URL patterns
   ↓
Fetch politely
   ↓
Cache
   ↓
Parse
   ↓
Normalize
   ↓
Validate
   ↓
Store
   ↓
Report
```

---

## 👨‍💻 Author

**Bavly Waleed**

FlyRank Internship — Week 5
Assignment A9 — The Polite Scraper
