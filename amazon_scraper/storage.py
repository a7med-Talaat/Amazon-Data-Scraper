import csv
import json
import os
import sqlite3
from datetime import datetime, timezone

from amazon_scraper import config
from amazon_scraper.utils import get_logger

log = get_logger("amazon_scraper.storage")

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    asin TEXT PRIMARY KEY,
    title TEXT,
    price REAL,
    rating REAL,
    review_count INTEGER,
    availability TEXT,
    url TEXT,
    image_url TEXT,
    bullet_points TEXT,
    keyword TEXT,
    scraped_at TEXT
);
"""


class Storage:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def save_products(self, products: list[dict], keyword: str = None) -> int:
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (
                p.get("asin"),
                p.get("title"),
                p.get("price"),
                p.get("rating"),
                p.get("review_count"),
                p.get("availability"),
                p.get("url"),
                p.get("image_url"),
                json.dumps(p.get("bullet_points") or []),
                keyword,
                now,
            )
            for p in products
            if p.get("asin")
        ]

        self.conn.executemany(
            """
            INSERT INTO products (asin, title, price, rating, review_count,
                                   availability, url, image_url, bullet_points,
                                   keyword, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asin) DO UPDATE SET
                title=excluded.title, price=excluded.price, rating=excluded.rating,
                review_count=excluded.review_count, availability=excluded.availability,
                url=excluded.url, image_url=excluded.image_url,
                bullet_points=excluded.bullet_points, keyword=excluded.keyword,
                scraped_at=excluded.scraped_at;
            """,
            rows,
        )
        self.conn.commit()
        log.info("Saved %d products to %s", len(rows), self.db_path)
        return len(rows)

    def fetch_all(self) -> list[dict]:
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.execute("SELECT * FROM products")
        return [dict(row) for row in cur.fetchall()]

    def export_csv(self, path: str = None) -> str:
        path = path or config.CSV_PRODUCTS_PATH
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        rows = self.fetch_all()

        if not rows:
            log.warning("No rows to export to CSV.")
            return path

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        log.info("Exported %d rows to %s", len(rows), path)
        return path

    def close(self):
        self.conn.close()
