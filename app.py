import streamlit as st
import pandas as pd
import os
import re
import json
import random
import time
from urllib.parse import quote_plus
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scrapling import Fetcher, Selector

st.set_page_config(
    page_title="Amazon Product Analyzer Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FF9900 0%, #FF5500 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1.15rem;
        color: #8C95A0;
        margin-bottom: 1.8rem;
    }
    .card {
        background-color: #1E222B;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border: 1px solid #2E323B;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🔍 Amazon Product Scraper & Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Enter keywords to scrape live product data, store in SQLite, export to CSV, and analyze findings instantly.</div>', unsafe_allow_html=True)

st.sidebar.markdown("### Scraper Controller")
st.sidebar.markdown("Configure and execute the Amazon scraping pipeline.")

region = st.sidebar.selectbox("🌍 Amazon Region", ["US (.com)", "Egypt (.eg)"])
amazon_domain = "com" if region == "US (.com)" else "eg"
base_url = f"https://www.amazon.{amazon_domain}"

keyword = st.sidebar.text_input("🔍 Search Keyword", value="", placeholder="e.g. wireless mouse")
max_results = st.sidebar.slider("🔢 Limit Scraped Results", min_value=1, max_value=50, value=10)

run_button = st.sidebar.button("🚀 Run Scraper Pipeline", type="primary", width="stretch")
clear_button = st.sidebar.button("🗑️ Clear Scraped Data", type="secondary", width="stretch")

if clear_button:
    from amazon_scraper.storage import Storage
    storage = Storage()
    storage.clear_all()
    storage.close()
    st.sidebar.success("🗑️ Scraped data deleted successfully!")
    time.sleep(1)
    st.rerun()

if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = []



def clean_text(text):
    if text is None:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def parse_price(text):
    if not text:
        return None
    match = re.search(r"[\d]+[.,]?\d*", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def parse_rating(text):
    if not text:
        return None
    match = re.search(r"(\d+(\.\d+)?)\s*out of", text)
    if match:
        return float(match.group(1))
    return None


def parse_review_count(text):
    if not text:
        return None
    match = re.search(r"[\d,]+", text)
    if not match:
        return None
    try:
        return int(match.group().replace(",", ""))
    except ValueError:
        return None


def fetch_url(url):
    from amazon_scraper import config
    
    impersonators = ["chrome", "edge", "safari", "firefox"]
    max_retries = getattr(config, "MAX_RETRIES", 3)
    backoff_factor = getattr(config, "BACKOFF_FACTOR", 2.0)
    
    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            imp = random.choice(impersonators)
            response = Fetcher.get(
                url,
                impersonate=imp,
                timeout=getattr(config, "REQUEST_TIMEOUT", 10.0)
            )
            
            if response.status != 200:
                raise Exception(f"HTTP status {response.status}")
                
            html_text = response.body.decode('utf-8', errors='ignore')
            
            # Check for CAPTCHA/bot-check page
            markers = (
                "Enter the characters you see below",
                "To discuss automated access to Amazon data",
                "api-services-support@amazon.com",
            )
            if any(marker in html_text for marker in markers):
                raise Exception("Amazon Bot-check/CAPTCHA page detected")
                
            return html_text
            
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                break
            wait = (backoff_factor ** (attempt - 1)) + random.uniform(0.5, 1.5)
            time.sleep(wait)
            
    raise Exception(f"Request failed after {max_retries} attempts: {last_exception}")



def parse_search_results(html):
    selector = Selector(html)
    results = []
    cards = selector.css('div[data-component-type="s-search-result"]')
    for card in cards:
        asin = card.css('::attr(data-asin)').get()
        title = clean_text(card.css("h2 span::text").get())
        link = card.css("h2 a::attr(href)").get() or card.css("a.a-link-normal::attr(href)").get()
        url = (base_url + link) if link else None
        price_text = card.css("span.a-price > span.a-offscreen::text").get()
        price = parse_price(price_text)
        rating_text = card.css("span.a-icon-alt::text").get()
        rating = parse_rating(rating_text)
        review_text = card.css('span[aria-label][class*="s-underline-text"]::text, span.a-size-base.s-underline-text::text').get()
        review_count = parse_review_count(review_text)
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


def parse_product_page(html, asin):
    selector = Selector(html)
    title = clean_text(selector.css("#productTitle::text").get())
    price_text = selector.css("span.a-price span.a-offscreen::text").get() or selector.css("#priceblock_ourprice::text").get() or selector.css("#priceblock_dealprice::text").get()
    price = parse_price(price_text)
    rating_text = selector.css("#acrPopover::attr(title)").get() or selector.css("span.a-icon-alt::text").get()
    rating = parse_rating(rating_text)
    review_text = selector.css("#acrCustomerReviewText::text").get()
    review_count = parse_review_count(review_text)
    availability = clean_text(selector.css("#availability span::text").get() or selector.css("#availability::text").get())

    bullets = []
    for text in selector.css("#feature-bullets li span::text").getall():
        cleaned = clean_text(text)
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


def save_products(products, kw):
    from amazon_scraper.storage import Storage
    storage = Storage()
    storage.save_products(products, keyword=kw)
    storage.close()


def load_db_data():
    from amazon_scraper.storage import Storage
    storage = Storage()
    rows = storage.fetch_all()
    storage.close()
    if not rows:
        return None
    for r in rows:
        if isinstance(r.get("bullet_points"), str):
            try:
                r["bullet_points"] = json.loads(r["bullet_points"])
            except Exception:
                pass
    return pd.DataFrame(rows)



def generate_report_content(df):
    stats = {"n_products": len(df)}
    for col in ("price", "rating", "review_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "price" in df.columns and df["price"].notna().any():
        stats["price_mean"] = round(df["price"].mean(), 2)
        stats["price_median"] = round(df["price"].median(), 2)
        stats["price_min"] = round(df["price"].min(), 2)
        stats["price_max"] = round(df["price"].max(), 2)
    if "rating" in df.columns and df["rating"].notna().any():
        stats["rating_mean"] = round(df["rating"].mean(), 2)
    if "review_count" in df.columns and df["review_count"].notna().any():
        stats["review_count_total"] = int(df["review_count"].sum())
        top = df.sort_values("review_count", ascending=False).head(1)
        if not top.empty:
            stats["most_reviewed_title"] = top.iloc[0].get("title")

    report_lines = [
        "# Amazon Scrape Analysis Report", "",
        f"Total products analysed: **{stats.get('n_products', 0)}**", ""
    ]
    if "price_mean" in stats:
        report_lines.extend([
            "## Price",
            f"- Mean: ${stats['price_mean']}",
            f"- Median: ${stats['price_median']}",
            f"- Range: ${stats['price_min']} - ${stats['price_max']}", ""
        ])
    if "rating_mean" in stats:
        report_lines.extend([
            "## Ratings",
            f"- Mean rating: {stats['rating_mean']} / 5", ""
        ])
    if "review_count_total" in stats:
        report_lines.extend([
            "## Reviews",
            f"- Total reviews across all products: {stats['review_count_total']}",
            f"- Most-reviewed product: {stats.get('most_reviewed_title')}", ""
        ])
    return "\n".join(report_lines)


if run_button:
    if not keyword.strip():
        st.sidebar.error("⚠️ Please specify a keyword to search.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("⚙️ Scraper Execution Status")
        status_text = st.empty()
        progress_bar = st.progress(0.0)

        try:
            status_text.info(f"Initiating request for keyword **'{keyword}'** on **Amazon {region}**...")
            progress_bar.progress(0.1)

            search_url = f"{base_url}/s?k={quote_plus(keyword)}"
            search_html = fetch_url(search_url)
            progress_bar.progress(0.4)

            search_results = parse_search_results(search_html)[:max_results]

            if not search_results:
                status_text.warning("⚠️ Amazon bot-check triggered or no results returned. Try again later.")
                progress_bar.progress(1.0)
            else:
                enriched = []
                for i, item in enumerate(search_results, start=1):
                    status_text.info(f"Enriching product {i}/{len(search_results)}: {item['asin']}...")
                    progress_bar.progress(0.4 + (i / len(search_results)) * 0.4)

                    try:
                        detail_url = f"{base_url}/dp/{item['asin']}"
                        detail_html = fetch_url(detail_url)
                        detail = parse_product_page(detail_html, item['asin'])
                        merged = {**item, **{k: v for k, v in detail.items() if v is not None}}
                        enriched.append(merged)
                    except Exception as e:
                        enriched.append(item)
                    time.sleep(random.uniform(3, 7))

                status_text.info("Saving items to SQLite database...")
                progress_bar.progress(0.9)
                save_products(enriched, keyword)

                status_text.success(f"🎉 Pipeline successfully completed! Scraped **{len(enriched)}** items.")
                progress_bar.progress(1.0)

        except Exception as e:
            status_text.error(f"❌ Scraper failed: {str(e)}")
            progress_bar.progress(1.0)
        st.markdown('</div>', unsafe_allow_html=True)

df = load_db_data()

tab_analytics, tab_table, tab_report = st.tabs([
    "📊 Market Dashboard & Analytics",
    "📋 Scraped Data Explorer",
    "📝 Markdown Report"
])

with tab_analytics:
    if df is not None and len(df) > 0:
        for col in ("price", "rating", "review_count"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        n_products = len(df)
        avg_price = df['price'].mean() if 'price' in df.columns else None
        avg_rating = df['rating'].mean() if 'rating' in df.columns else None
        total_reviews = df['review_count'].sum() if 'review_count' in df.columns else None

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Items Scraped", f"{n_products}")
        with col2:
            st.metric("Average Price", f"${avg_price:.2f}" if pd.notna(avg_price) else "N/A")
        with col3:
            st.metric("Average Rating", f"{avg_rating:.2f} / 5" if pd.notna(avg_rating) else "N/A")
        with col4:
            st.metric("Total Reviews Scraped", f"{int(total_reviews):,}" if pd.notna(total_reviews) else "N/A")

        st.markdown("---")
        st.subheader("Visual Market Distribution")
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            if "price" in df.columns and df["price"].notna().sum() > 0:
                fig, ax = plt.subplots(figsize=(7, 4))
                df["price"].dropna().plot(kind="hist", bins=15, ax=ax, color="#4C72B0", edgecolor="white")
                ax.set_title("Price distribution")
                ax.set_xlabel("Price ($)")
                ax.set_ylabel("Number of products")
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

            if "review_count" in df.columns and "title" in df.columns:
                top_10 = df.dropna(subset=["review_count"]).sort_values("review_count", ascending=False).head(10)
                if not top_10.empty:
                    fig, ax = plt.subplots(figsize=(8, 5))
                    labels = [t[:40] + ("…" if len(t) > 40 else "") for t in top_10["title"]]
                    ax.barh(labels[::-1], top_10["review_count"][::-1], color="#55A868")
                    ax.set_title("Top 10 most-reviewed products")
                    ax.set_xlabel("Number of reviews")
                    fig.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)

        with col_c2:
            if {"price", "rating"}.issubset(df.columns) and df[["price", "rating"]].dropna().shape[0] > 1:
                fig, ax = plt.subplots(figsize=(7, 4))
                sub = df.dropna(subset=["price", "rating"])
                ax.scatter(sub["price"], sub["rating"], alpha=0.6, color="#DD8452")
                ax.set_title("Rating vs. price")
                ax.set_xlabel("Price ($)")
                ax.set_ylabel("Rating (out of 5)")
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)
    else:
        st.info("💡 Run the scraper using the sidebar panel to see analytics and metrics.")

with tab_table:
    if df is not None and len(df) > 0:
        st.subheader("All Scraped Products")
        all_keywords = df['keyword'].dropna().unique()
        selected_key = st.selectbox("🎯 Filter data by Search Keyword:", ["Show All"] + list(all_keywords))

        view_df = df
        if selected_key != "Show All":
            view_df = df[df['keyword'] == selected_key]

        cols = ["asin", "title", "price", "rating", "review_count", "availability", "url", "scraped_at"]
        cols = [c for c in cols if c in view_df.columns]

        st.dataframe(view_df[cols], width="stretch")

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            csv_str = view_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download current table as CSV",
                data=csv_str,
                file_name="scraped_amazon_products.csv",
                mime="text/csv",
                width="stretch"
            )
    else:
        st.info("💡 No database records found yet. Execute a scrape from the sidebar to populate the database.")

with tab_report:
    if df is not None and len(df) > 0:
        st.subheader("Generated Analysis Report")
        report_content = generate_report_content(df.copy())
        st.markdown(report_content)
    else:
        st.info("💡 No markdown analysis report exists yet. Run a scrape to generate the report.")
