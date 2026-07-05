import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from amazon_scraper import config
from amazon_scraper.utils import get_logger

log = get_logger("amazon_scraper.analysis")


def load_dataframe(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for col in ("price", "rating"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "review_count" in df.columns:
        df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce")
    return df


def summary_stats(df: pd.DataFrame) -> dict:
    stats = {"n_products": len(df)}
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
    return stats


def make_charts(df: pd.DataFrame, out_dir: str = None) -> list[str]:
    out_dir = out_dir or config.REPORT_DIR
    os.makedirs(out_dir, exist_ok=True)
    paths = []

    if "price" in df.columns and df["price"].notna().sum() > 0:
        fig, ax = plt.subplots(figsize=(7, 4))
        df["price"].dropna().plot(kind="hist", bins=15, ax=ax, color="#4C72B0", edgecolor="white")
        ax.set_title("Price distribution")
        ax.set_xlabel("Price ($)")
        ax.set_ylabel("Number of products")
        fig.tight_layout()
        path = os.path.join(out_dir, "price_distribution.png")
        fig.savefig(path, dpi=120)
        plt.close(fig)
        paths.append(path)

    if {"price", "rating"}.issubset(df.columns) and df[["price", "rating"]].dropna().shape[0] > 1:
        fig, ax = plt.subplots(figsize=(7, 4))
        sub = df.dropna(subset=["price", "rating"])
        ax.scatter(sub["price"], sub["rating"], alpha=0.6, color="#DD8452")
        ax.set_title("Rating vs. price")
        ax.set_xlabel("Price ($)")
        ax.set_ylabel("Rating (out of 5)")
        fig.tight_layout()
        path = os.path.join(out_dir, "rating_vs_price.png")
        fig.savefig(path, dpi=120)
        plt.close(fig)
        paths.append(path)

    if "review_count" in df.columns and "title" in df.columns:
        top = df.dropna(subset=["review_count"]).sort_values("review_count", ascending=False).head(10)
        if not top.empty:
            fig, ax = plt.subplots(figsize=(8, 5))
            labels = [t[:40] + ("…" if len(t) > 40 else "") for t in top["title"]]
            ax.barh(labels[::-1], top["review_count"][::-1], color="#55A868")
            ax.set_title("Top 10 most-reviewed products")
            ax.set_xlabel("Number of reviews")
            fig.tight_layout()
            path = os.path.join(out_dir, "top_reviewed.png")
            fig.savefig(path, dpi=120)
            plt.close(fig)
            paths.append(path)

    log.info("Generated %d chart(s) in %s", len(paths), out_dir)
    return paths


def write_text_report(stats: dict, chart_paths: list[str], out_dir: str = None) -> str:
    out_dir = out_dir or config.REPORT_DIR
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "report.md")

    lines = ["# Amazon Scrape Analysis Report", ""]
    lines.append(f"Total products analysed: **{stats.get('n_products', 0)}**")
    lines.append("")
    if "price_mean" in stats:
        lines.append("## Price")
        lines.append(f"- Mean: ${stats['price_mean']}")
        lines.append(f"- Median: ${stats['price_median']}")
        lines.append(f"- Range: ${stats['price_min']} - ${stats['price_max']}")
        lines.append("")
    if "rating_mean" in stats:
        lines.append("## Ratings")
        lines.append(f"- Mean rating: {stats['rating_mean']} / 5")
        lines.append("")
    if "review_count_total" in stats:
        lines.append("## Reviews")
        lines.append(f"- Total reviews across all products: {stats['review_count_total']}")
        if stats.get("most_reviewed_title"):
            lines.append(f"- Most-reviewed product: {stats['most_reviewed_title']}")
        lines.append("")
    if chart_paths:
        lines.append("## Charts")
        for path in chart_paths:
            lines.append(f"- {os.path.basename(path)}")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log.info("Wrote text report to %s", report_path)
    return report_path


def run_analysis(rows: list[dict], out_dir: str = None) -> dict:
    df = load_dataframe(rows)
    stats = summary_stats(df)
    charts = make_charts(df, out_dir=out_dir)
    report_path = write_text_report(stats, charts, out_dir=out_dir)
    return {"stats": stats, "charts": charts, "report_path": report_path}
