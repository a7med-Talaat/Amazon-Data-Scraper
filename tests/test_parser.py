"""
Tests for the pure parsing functions.

These run entirely offline against saved HTML fixtures, so they're fast,
deterministic, and don't depend on Amazon being reachable or serving
consistent markup at test time.
"""

import os

import pytest

from amazon_scraper import parser

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name: str) -> str:
    with open(os.path.join(FIXTURES_DIR, name), encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def search_html():
    return _load_fixture("search_results_sample.html")


@pytest.fixture
def product_html():
    return _load_fixture("product_page_sample.html")


class TestParseSearchResults:
    def test_returns_expected_count(self, search_html):
        results = parser.parse_search_results(search_html)
        # 4 cards in fixture, 1 malformed (no asin/title) should be skipped
        assert len(results) == 3

    def test_skips_cards_missing_asin_or_title(self, search_html):
        results = parser.parse_search_results(search_html)
        assert all(r["asin"] and r["title"] for r in results)

    def test_extracts_expected_fields(self, search_html):
        results = parser.parse_search_results(search_html)
        first = results[0]
        assert first["asin"] == "B0EXAMPLE1"
        assert "Logitech" in first["title"]
        assert first["price"] == 14.99
        assert first["rating"] == 4.5
        assert first["review_count"] == 12340
        assert first["url"].endswith("/dp/B0EXAMPLE1")
        assert first["image_url"] == "https://example.com/images/mouse1.jpg"

    def test_handles_empty_html(self):
        assert parser.parse_search_results("<html></html>") == []


class TestParseProductPage:
    def test_extracts_title(self, product_html):
        product = parser.parse_product_page(product_html, asin="B0EXAMPLE1")
        assert "Logitech M185" in product["title"]

    def test_extracts_price(self, product_html):
        product = parser.parse_product_page(product_html, asin="B0EXAMPLE1")
        assert product["price"] == 14.99

    def test_extracts_rating_and_reviews(self, product_html):
        product = parser.parse_product_page(product_html, asin="B0EXAMPLE1")
        assert product["rating"] == 4.5
        assert product["review_count"] == 12340

    def test_extracts_availability(self, product_html):
        product = parser.parse_product_page(product_html, asin="B0EXAMPLE1")
        assert "In Stock" in product["availability"]

    def test_extracts_bullet_points(self, product_html):
        product = parser.parse_product_page(product_html, asin="B0EXAMPLE1")
        assert len(product["bullet_points"]) == 3
        assert any("battery life" in b for b in product["bullet_points"])

    def test_extracts_image(self, product_html):
        product = parser.parse_product_page(product_html, asin="B0EXAMPLE1")
        assert product["image_url"] == "https://example.com/images/mouse1_hires.jpg"

    def test_handles_missing_fields_gracefully(self):
        product = parser.parse_product_page("<html><body></body></html>", asin="B0MISSING")
        assert product["asin"] == "B0MISSING"
        assert product["title"] is None
        assert product["price"] is None
        assert product["bullet_points"] == []


class TestHelperFunctions:
    @pytest.mark.parametrize("text,expected", [
        ("$19.99", 19.99),
        ("$1,299.00", 1299.00),
        (None, None),
        ("Free", None),
    ])
    def test_parse_price(self, text, expected):
        assert parser._parse_price(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("4.5 out of 5 stars", 4.5),
        ("3 out of 5 stars", 3.0),
        (None, None),
        ("no rating here", None),
    ])
    def test_parse_rating(self, text, expected):
        assert parser._parse_rating(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("1,234 ratings", 1234),
        ("842", 842),
        (None, None),
    ])
    def test_parse_review_count(self, text, expected):
        assert parser._parse_review_count(text) == expected
