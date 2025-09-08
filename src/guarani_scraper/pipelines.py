# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import json
from datetime import datetime
from urllib.parse import urlparse
from itemadapter import ItemAdapter


class GuaraniScraperPipeline:
    """
    Pipeline for processing and storing scraped content.

    Each domain's content is saved to a JSONL file with fields:
    - text: The concatenated scraped content of the page.
    - date: The timestamp when the page was scraped.
    - url: The URL of the page.
    """

    def __init__(self):
        """Initialize the pipeline."""
        self.files = {}
        self.corpus_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "corpus")
        os.makedirs(self.corpus_dir, exist_ok=True)

    def get_clean_domain(self, url):
        """Extract clean domain name without TLD extensions."""
        domain = urlparse(url).netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def process_item(self, item, spider):
        """Process an item by appending a new line for each scraped item."""
        adapter = ItemAdapter(item)

        # Get the URL and clean domain
        url = adapter["url"]
        clean_domain = self.get_clean_domain(url)

        # Create domain directory
        domain_dir = os.path.join(self.corpus_dir, clean_domain)
        os.makedirs(domain_dir, exist_ok=True)

        # Create file path for the JSONL file
        file_path = os.path.join(domain_dir, f"{clean_domain}.jsonl")

        # Create a new entry for the URL
        record = {
            "text": adapter["word"],
            "date": datetime.utcnow().isoformat(),
            "url": url
        }

        # Append the new record to the file
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return item

    def close_spider(self, spider):
        """Close all open files when spider finishes."""
        for file_handle in self.files.values():
            file_handle.close()
