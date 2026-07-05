from urllib.parse import quote_plus

from scrapling import Fetcher

from amazon_scraper import config, parser
from amazon_scraper.utils import get_logger, polite_delay, retry_with_backoff

log = get_logger("amazon_scraper.scraper")


class BlockedError(Exception):
    pass


class AmazonScraper:
    def __init__(self):
        self.proxy = config.PROXY

    @retry_with_backoff()
    def _get(self, url: str) -> str:
        headers = config.random_headers()
        response = Fetcher.get(
            url,
            headers=headers,
            proxy=self.proxy,
            timeout=config.REQUEST_TIMEOUT
        )

        if response.status != 200:
            raise BlockedError(f"Request failed with status {response.status} at {url}")

        html_text = response.body.decode('utf-8', errors='ignore')
        if self._looks_blocked(html_text):
            raise BlockedError(f"Bot-check / CAPTCHA page detected at {url}")

        return html_text

    @staticmethod
    def _looks_blocked(html: str) -> bool:
        markers = (
            "Enter the characters you see below",
            "To discuss automated access to Amazon data",
            "api-services-support@amazon.com",
        )
        return any(marker in html for marker in markers)

    def search(self, keyword: str, max_results: int = 20) -> list[dict]:
        url = f"{config.BASE_URL}/s?k={quote_plus(keyword)}"
        log.info("Searching: %s", url)

        try:
            html = self._get(url)
        except BlockedError as exc:
            log.error(str(exc))
            return []

        results = parser.parse_search_results(html)
        polite_delay()
        return results[:max_results]

    def get_product(self, asin: str) -> dict | None:
        url = f"{config.BASE_URL}/dp/{asin}"
        log.info("Fetching product: %s", url)

        try:
            html = self._get(url)
        except BlockedError as exc:
            log.error(str(exc))
            return None

        product = parser.parse_product_page(html, asin=asin)
        polite_delay()
        return product

    def search_and_enrich(self, keyword: str, max_results: int = 10) -> list[dict]:
        search_results = self.search(keyword, max_results=max_results)
        enriched = []

        for i, item in enumerate(search_results, start=1):
            log.info("Enriching %d/%d: %s", i, len(search_results), item["asin"])
            detail = self.get_product(item["asin"]) or {}
            merged = {**item, **{k: v for k, v in detail.items() if v is not None}}
            enriched.append(merged)

        return enriched
