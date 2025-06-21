import argparse
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from src.guarani_scraper.spiders.guarani_spider import GuaraniSpider


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
    group.add_argument(
        "--csv", help="CSV file with columns: name,description,url"
    )
    group.add_argument(
        "--url", help="Single URL to scrape for Guarani words"
    )

    args = parser.parse_args()
    
    # Prepare spider arguments
    spider_kwargs = {}
    if args.csv:
        spider_kwargs['csv_file'] = args.csv
    elif args.url:
        spider_kwargs['single_url'] = args.url

    process = CrawlerProcess(get_project_settings())
    process.crawl(GuaraniSpider, **spider_kwargs)
    process.start()


if __name__ == "__main__":
    main()
