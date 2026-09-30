# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import json
from datetime import datetime
from itemadapter import ItemAdapter
from .utils import crawl_state


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
        self.corpus_dir = str(crawl_state.DATA_DIR)
        self._previous_urls = {}
        os.makedirs(self.corpus_dir, exist_ok=True)

    def get_clean_domain(self, url):
        """Extract hostname, removing only the exact www. prefix."""
        return crawl_state.clean_domain(url)

    def process_item(self, item, spider):
        """Process an item by appending a new line for each scraped item."""
        adapter = ItemAdapter(item)

        # Get the URL and clean domain
        url = adapter["url"]
        text = adapter["word"]
        file_path = str(crawl_state.download_path(url, self.corpus_dir))
        # Snapshot pre-existing URLs before writing the first chunk for a domain.
        # New chunks for the same page in this run must still be merged.
        if file_path not in self._previous_urls:
            self._previous_urls[file_path] = crawl_state.read_url_keys(file_path)
        key = crawl_state.url_key(url)
        if key in self._previous_urls[file_path]:
            return item

        domain_dir = os.path.dirname(file_path)
        os.makedirs(domain_dir, exist_ok=True)

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

                    try:
                        existing_key = crawl_state.url_key(obj.get("url", "")) if isinstance(obj, dict) else None
                    except (ValueError, TypeError):
                        existing_key = None
                    if existing_key == key:
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
