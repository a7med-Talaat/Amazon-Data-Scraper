import re
from typing import Optional

from scrapling import Selector

from amazon_scraper import config


def _clean_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"[\d]+[.,]?\d*", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _parse_rating(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"(\d+(\.\d+)?)\s*out of", text)
    if match:
        return float(match.group(1))
    return None


def _parse_review_count(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    match = re.search(r"[\d,]+", text)
    if not match:
        return None
    try:
        return int(match.group().replace(",", ""))
    except ValueError:
        return None


def parse_search_results(html: str) -> list[dict]:
    selector = Selector(html)
    results = []

    cards = selector.css('div[data-component-type="s-search-result"]')

    for card in cards:
        asin = card.css('::attr(data-asin)').get()
        title = _clean_text(card.css("h2 span::text").get())

        link = card.css("h2 a::attr(href)").get() or card.css("a.a-link-normal::attr(href)").get()
        url = (config.BASE_URL + link) if link else None

        price_text = card.css("span.a-price > span.a-offscreen::text").get()
        price = _parse_price(price_text)

        rating_text = card.css("span.a-icon-alt::text").get()
        rating = _parse_rating(rating_text)

        review_text = card.css('span[aria-label][class*="s-underline-text"]::text, span.a-size-base.s-underline-text::text').get()
        review_count = _parse_review_count(review_text)

        image_url = card.css("img.s-image::attr(src)").get()

        if not (asin and title):
            continue

        results.append({
            "asin": asin,
            "title": title,
            "url": url,
            "price": price,
            "rating": rating,
            "review_count": review_count,
            "image_url": image_url,
        })

    return results


def parse_product_page(html: str, asin: str = None) -> dict:
    selector = Selector(html)

    title = _clean_text(selector.css("#productTitle::text").get())

    price_text = selector.css("span.a-price span.a-offscreen::text").get() or selector.css("#priceblock_ourprice::text").get() or selector.css("#priceblock_dealprice::text").get()
    price = _parse_price(price_text)

    rating_text = selector.css("#acrPopover::attr(title)").get() or selector.css("span.a-icon-alt::text").get()
    rating = _parse_rating(rating_text)

    review_text = selector.css("#acrCustomerReviewText::text").get()
    review_count = _parse_review_count(review_text)

    availability = _clean_text(selector.css("#availability span::text").get() or selector.css("#availability::text").get())

    bullets = []
    for text in selector.css("#feature-bullets li span::text").getall():
        cleaned = _clean_text(text)
        if cleaned:
            bullets.append(cleaned)

    image_el = selector.css("#imgTagWrapperId img, #landingImage")
    image_url = image_el.css("::attr(data-old-hires)").get() or image_el.css("::attr(src)").get()

    return {
        "asin": asin,
        "title": title,
        "price": price,
        "rating": rating,
        "review_count": review_count,
        "availability": availability,
        "bullet_points": bullets,
        "image_url": image_url,
    }
