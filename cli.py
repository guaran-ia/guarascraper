import sys
import os
import argparse
import logging
from logging.handlers import RotatingFileHandler
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Add src to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Ensure logs directory exists and configure an error log file
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "scraper_errors.log")
handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
# Capture INFO and above (INFO, WARNING, ERROR, CRITICAL) go to file
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
root_logger = logging.getLogger()
# Set root logger level to INFO so file receives INFO and ERROR only
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)


def main():
    """
    Main entry point for the Guarani scraper CLI.

    Parses command-line arguments and starts the crawler process
    to scrape Guarani words from websites listed in the provided CSV file or from a single URL.

    Command-line arguments:
        --csv: Path to a CSV file with columns: name,description,url
        --url: Single URL to scrape for Guarani words
    """
    parser = argparse.ArgumentParser(
        description="Scraper de palabras en guarani de sitios web."
    )

    # Mutually exclusive group - only one of these parameters
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--csv", help="CSV file with columns: name,description,url")
    group.add_argument("--url", help="Single URL to scrape for Guarani words")

    # When using a single URL, allow choosing whether to crawl the whole domain
    # or only the single page. The --crawl-domain flag will be passed to the
    # spider as the `crawl_domain` kwarg.
    parser.add_argument(
        "--crawl-domain",
        action="store_true",
        help="When used with --url, crawl the whole domain instead of only the page",
    )

    args = parser.parse_args()

    # Import the spider after argument parsing so --help is available without
    # the optional external language-identifier checkout.
    from scraper.spider import GuaraniSpider

    # Prepare spider arguments
    spider_kwargs = {}
    if args.csv:
        spider_kwargs["csv_file"] = os.path.abspath(args.csv)
        spider_kwargs["crawl_domain"] = bool(args.crawl_domain)
    elif args.url:
        spider_kwargs["single_url"] = args.url
        spider_kwargs["crawl_domain"] = bool(args.crawl_domain)

    # Change working directory to src for scrapy to work properly
    original_dir = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(__file__), "src"))

    try:
        process = CrawlerProcess(get_project_settings())
        process.crawl(GuaraniSpider, **spider_kwargs)
        process.start()
    finally:
        # Restore original working directory
        os.chdir(original_dir)


if __name__ == "__main__":
    main()
