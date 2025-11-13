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
        self.corpus_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")
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
        text = adapter["word"]
        clean_domain = self.get_clean_domain(url)

        # Create domain directory
        domain_dir = os.path.join(self.corpus_dir, 'download')
        os.makedirs(domain_dir, exist_ok=True)

        # Create file path for the JSONL file
        file_path = os.path.join(domain_dir, f"{clean_domain}.jsonl")

        # If file exists and contains the URL, merge by concatenating text
        if os.path.exists(file_path):
            merged = False
            out_lines = []
            with open(file_path, "r", encoding="utf-8") as rf:
                for line in rf:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        out_lines.append(line)
                        continue

                    if obj.get("url") == url:
                        # concatenate texts
                        existing = obj.get("text", "")
                        combined = "\n".join([p for p in [existing, text] if p])
                        obj["text"] = combined
                        obj["date"] = datetime.utcnow().isoformat()
                        out_lines.append(json.dumps(obj, ensure_ascii=False))
                        merged = True
                    else:
                        out_lines.append(json.dumps(obj, ensure_ascii=False))

            if not merged:
                # append new record
                record = {"text": text, "date": datetime.utcnow().isoformat(), "url": url}
                out_lines.append(json.dumps(record, ensure_ascii=False))

            # write atomically
            tmp_path = file_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as wf:
                for l in out_lines:
                    wf.write(l + "\n")
            os.replace(tmp_path, file_path)
        else:
            # Create a new entry for the URL and append
            record = {"text": text, "date": datetime.utcnow().isoformat(), "url": url}
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return item

    def close_spider(self, spider):
        """Close all open files when spider finishes."""
        for file_handle in self.files.values():
            file_handle.close()
