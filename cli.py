import argparse
import sys

from amazon_scraper import config
from amazon_scraper.analysis import run_analysis
from amazon_scraper.scraper import AmazonScraper
from amazon_scraper.storage import Storage
from amazon_scraper.utils import get_logger

log = get_logger("amazon_scraper.cli")


def cmd_run(args):
    scraper = AmazonScraper()
    storage = Storage(db_path=args.db)

    log.info("Starting search+enrich for keyword=%r, max_results=%d", args.keyword, args.max_results)
    products = scraper.search_and_enrich(args.keyword, max_results=args.max_results)

    if not products:
        log.warning(
            "No products were scraped. This usually means Amazon served a "
            "CAPTCHA/bot-check page, or the keyword returned no results. "
            "See README's 'Known limitations' section."
        )
        storage.close()
        sys.exit(1)

    storage.save_products(products, keyword=args.keyword)
    storage.export_csv(args.csv)

    rows = storage.fetch_all()
    result = run_analysis(rows, out_dir=args.report_dir)
    storage.close()

    log.info("Done. %d products in DB. Report at %s", len(rows), result["report_path"])
    print(f"\nSummary: {result['stats']}")


def cmd_analyze(args):
    storage = Storage(db_path=args.db)
    rows = storage.fetch_all()
    storage.close()

    if not rows:
        log.warning("Database is empty - nothing to analyze. Run 'run' first.")
        sys.exit(1)

    result = run_analysis(rows, out_dir=args.report_dir)
    print(f"Summary: {result['stats']}")
    print(f"Report written to: {result['report_path']}")


def cmd_export(args):
    storage = Storage(db_path=args.db)
    path = storage.export_csv(args.csv)
    storage.close()
    print(f"Exported to: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Amazon search + product scraper toolkit")
    parser.add_argument("--db", default=config.DB_PATH, help="Path to SQLite database file")

    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Search, enrich, store, and analyze in one pipeline")
    p_run.add_argument("--keyword", required=True, help="Search term, e.g. 'wireless mouse'")
    p_run.add_argument("--max-results", type=int, default=10, help="Max number of products to scrape")
    p_run.add_argument("--csv", default=config.CSV_PRODUCTS_PATH, help="CSV export path")
    p_run.add_argument("--report-dir", default=config.REPORT_DIR, help="Directory for charts/report")
    p_run.set_defaults(func=cmd_run)

    p_analyze = sub.add_parser("analyze", help="Re-run analysis on existing database contents")
    p_analyze.add_argument("--report-dir", default=config.REPORT_DIR, help="Directory for charts/report")
    p_analyze.set_defaults(func=cmd_analyze)

    p_export = sub.add_parser("export", help="Export current database contents to CSV")
    p_export.add_argument("--csv", default=config.CSV_PRODUCTS_PATH, help="CSV export path")
    p_export.set_defaults(func=cmd_export)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
