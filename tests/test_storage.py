"""Tests for SQLite storage and CSV export, using a temp DB per test."""

import csv

from amazon_scraper.storage import Storage

SAMPLE_PRODUCTS = [
    {
        "asin": "B0EXAMPLE1",
        "title": "Logitech M185 Wireless Mouse",
        "price": 14.99,
        "rating": 4.5,
        "review_count": 12340,
        "availability": "In Stock",
        "url": "https://www.amazon.com/dp/B0EXAMPLE1",
        "image_url": "https://example.com/mouse1.jpg",
        "bullet_points": ["Wireless", "Long battery life"],
    },
    {
        "asin": "B0EXAMPLE2",
        "title": "Razer DeathAdder V3",
        "price": 49.99,
        "rating": 4.7,
        "review_count": 5201,
        "availability": "In Stock",
        "url": "https://www.amazon.com/dp/B0EXAMPLE2",
        "image_url": "https://example.com/mouse2.jpg",
        "bullet_points": [],
    },
]


def make_storage(tmp_path):
    return Storage(db_path=str(tmp_path / "test.db"))


class TestStorage:
    def test_save_and_fetch(self, tmp_path):
        store = make_storage(tmp_path)
        written = store.save_products(SAMPLE_PRODUCTS, keyword="wireless mouse")
        assert written == 2

        rows = store.fetch_all()
        assert len(rows) == 2
        asins = {r["asin"] for r in rows}
        assert asins == {"B0EXAMPLE1", "B0EXAMPLE2"}
        store.close()

    def test_upsert_updates_existing_row(self, tmp_path):
        store = make_storage(tmp_path)
        store.save_products(SAMPLE_PRODUCTS, keyword="wireless mouse")

        updated = dict(SAMPLE_PRODUCTS[0])
        updated["price"] = 9.99
        store.save_products([updated], keyword="wireless mouse")

        rows = store.fetch_all()
        assert len(rows) == 2  # still 2 rows, not 3 - upsert not insert
        row = next(r for r in rows if r["asin"] == "B0EXAMPLE1")
        assert row["price"] == 9.99
        store.close()

    def test_skips_rows_without_asin(self, tmp_path):
        store = make_storage(tmp_path)
        written = store.save_products([{"title": "No ASIN here"}])
        assert written == 0
        store.close()

    def test_export_csv(self, tmp_path):
        store = make_storage(tmp_path)
        store.save_products(SAMPLE_PRODUCTS, keyword="wireless mouse")

        csv_path = str(tmp_path / "out.csv")
        store.export_csv(csv_path)

        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert "title" in rows[0]
        store.close()

    def test_export_csv_with_no_data(self, tmp_path):
        store = make_storage(tmp_path)
        csv_path = str(tmp_path / "empty.csv")
        store.export_csv(csv_path)
        # Should not raise, and file need not exist if there's nothing to write
        store.close()

    def test_clear_all(self, tmp_path):
        store = make_storage(tmp_path)
        store.save_products(SAMPLE_PRODUCTS, keyword="wireless mouse")
        assert len(store.fetch_all()) == 2
        store.clear_all()
        assert len(store.fetch_all()) == 0
        store.close()

