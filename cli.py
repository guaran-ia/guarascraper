import sys
import os
import argparse
import logging
import math
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


def nonnegative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return number


def nonnegative_seconds(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be a finite, non-negative number")
    return number


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
        help="Follow links within the input domains (subject to crawl limits)",
    )
    parser.add_argument("--max-depth", type=nonnegative_int,
                        help="Maximum link depth (default: 3; 0 disables the limit)")
    parser.add_argument("--max-pages", type=nonnegative_int,
                        help="Response-count shutdown threshold for the whole run (default: 500; 0 disables)")
    parser.add_argument("--timeout", type=nonnegative_seconds,
                        help="Whole-run shutdown timeout in seconds (default: 600; 0 disables)")
    parser.add_argument("--download-delay", type=nonnegative_seconds,
                        help="Minimum per-domain delay in seconds (default: 2; AutoThrottle may increase it)")

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
        settings = get_project_settings()
        for setting, value in (
            ("DEPTH_LIMIT", args.max_depth),
            ("CLOSESPIDER_PAGECOUNT", args.max_pages),
            ("CLOSESPIDER_TIMEOUT", args.timeout),
            ("DOWNLOAD_DELAY", args.download_delay),
        ):
            if value is not None:
                settings.set(setting, value, priority="cmdline")
        # AutoThrottle clamps to its maximum: keep it above the requested floor.
        settings.set(
            "AUTOTHROTTLE_MAX_DELAY",
            max(settings.getfloat("AUTOTHROTTLE_MAX_DELAY"), settings.getfloat("DOWNLOAD_DELAY")),
            priority="cmdline",
        )
        process = CrawlerProcess(settings)
        logging.getLogger(__name__).info(
            "Crawl policy: user_agent=%s robots_agent=%s robots_obey=%s "
            "max_depth=%s max_pages=%s timeout=%ss download_delay=%ss "
            "concurrency=%s per_domain=%s autothrottle=%s autothrottle_max_delay=%ss",
            settings.get("USER_AGENT"), settings.get("ROBOTSTXT_USER_AGENT"),
            settings.getbool("ROBOTSTXT_OBEY"), settings.getint("DEPTH_LIMIT"),
            settings.getint("CLOSESPIDER_PAGECOUNT"), settings.getfloat("CLOSESPIDER_TIMEOUT"),
            settings.getfloat("DOWNLOAD_DELAY"), settings.getint("CONCURRENT_REQUESTS"),
            settings.getint("CONCURRENT_REQUESTS_PER_DOMAIN"), settings.getbool("AUTOTHROTTLE_ENABLED"),
            settings.getfloat("AUTOTHROTTLE_MAX_DELAY"),
        )
        process.crawl(GuaraniSpider, **spider_kwargs)
        process.start()
    finally:
        # Restore original working directory
        os.chdir(original_dir)


if __name__ == "__main__":
    main()
