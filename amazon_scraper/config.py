import os
import random

AMAZON_DOMAIN = os.getenv("AMAZON_DOMAIN", "com")
BASE_URL = f"https://www.amazon.{AMAZON_DOMAIN}"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36",
]


def random_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


MIN_DELAY = float(os.getenv("SCRAPER_MIN_DELAY", 3.0))
MAX_DELAY = float(os.getenv("SCRAPER_MAX_DELAY", 7.0))

MAX_RETRIES = int(os.getenv("SCRAPER_MAX_RETRIES", 3))
BACKOFF_FACTOR = float(os.getenv("SCRAPER_BACKOFF_FACTOR", 2.0))
REQUEST_TIMEOUT = float(os.getenv("SCRAPER_TIMEOUT", 10.0))

PROXY = os.getenv("SCRAPER_PROXY", "").strip() or None

DB_PATH = os.getenv("SCRAPER_DB_PATH", "output/amazon_data.db")
CSV_SEARCH_PATH = os.getenv("SCRAPER_CSV_SEARCH", "output/search_results.csv")
CSV_PRODUCTS_PATH = os.getenv("SCRAPER_CSV_PRODUCTS", "output/products.csv")
REPORT_DIR = os.getenv("SCRAPER_REPORT_DIR", "output/report")
