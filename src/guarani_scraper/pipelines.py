# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import re
import json
from urllib.parse import urlparse, parse_qs
from itemadapter import ItemAdapter


class GuaraniScraperPipeline:
    """
    Pipeline for processing and storing scraped Guarani words.

    Words are saved to text files organized by domain and page:
    corpus/domain_name/page_path.txt
    """

    def __init__(self):
        """Initialize the pipeline."""
        self.files = {}
        self.domain_metadata = {}
        # Use absolute path to ensure consistency
        self.corpus_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "corpus")
        os.makedirs(self.corpus_dir, exist_ok=True)

    def get_clean_domain(self, url):
        """Extract clean domain name without TLD extensions."""
        domain = urlparse(url).netloc

        # Remove common prefixes
        if domain.startswith("www."):
            domain = domain[4:]

        # Remove top level domain extensions
        domain = re.sub(r"\.(com|org|edu|gov|py|blogspot\.com)$", "", domain)

        return domain
    
    def get_original_domain(self, url):
        """Get the original domain with TLD for metadata."""
        domain = urlparse(url).netloc
        # Remove www but keep TLD
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def get_clean_path(self, url):
        """Convert URL path to clean filename."""
        parsed = urlparse(url)
        path = parsed.path
        query = parsed.query

        # Handle root path
        if not path or path == "/":
            filename = "index"
        else:
            # Remove leading/trailing slashes and replace separators
            filename = path.strip("/").replace("/", "_")
            # Remove file extensions
            filename = re.sub(r"\.(html|php|htm)$", "", filename)

        # Handle query parameters
        if query:
            query_parts = []
            params = parse_qs(query)
            for key, values in params.items():
                for value in values:
                    query_parts.append(f"{key}_{value}")
            if query_parts:
                filename += "_" + "_".join(query_parts)

        # Clean filename - only alphanumeric, underscore, hyphen
        filename = re.sub(r"[^\w\-_]", "_", filename)
        # Remove multiple consecutive underscores
        filename = re.sub(r"_+", "_", filename)
        # Remove leading/trailing underscores
        filename = filename.strip("_")

        return filename + ".txt"

    def process_item(self, item, spider):
        """Process a GuaraniWord item by writing it to the appropriate file."""
        adapter = ItemAdapter(item)

        # Get clean domain and original domain
        clean_domain = self.get_clean_domain(adapter["url"])
        original_domain = self.get_original_domain(adapter["url"])
        filename = self.get_clean_path(adapter["url"])

        # Create domain directory
        domain_dir = os.path.join(self.corpus_dir, clean_domain)
        os.makedirs(domain_dir, exist_ok=True)

        # Create file path
        file_path = os.path.join(domain_dir, filename)

        # Open file if not already open
        if file_path not in self.files:
            self.files[file_path] = open(file_path, "w", encoding="utf-8")

        # Write word to file
        self.files[file_path].write(adapter["word"] + "\n")
        self.files[file_path].flush()

        # Track metadata for JSON
        if clean_domain not in self.domain_metadata:
            self.domain_metadata[clean_domain] = []

        # Create metadata entry for this page
        page_metadata = {
            'dominio': original_domain,
            'web_page_url': adapter["url"],
            'file_web_page_content': f'corpus/{clean_domain}/{filename}'
        }

        # Check if this page is already in metadata (avoid duplicates)
        existing_entry = next((entry for entry in self.domain_metadata[clean_domain] 
                              if entry['web_page_url'] == adapter["url"]), None)
        
        if not existing_entry:
            self.domain_metadata[clean_domain].append(page_metadata)

        return item

    def close_spider(self, spider):
        """Close all open files and create JSON metadata files when spider finishes."""
        # Close all text files
        for file_handle in self.files.values():
            file_handle.close()

        # Create JSON files for each domain
        for clean_domain, metadata_list in self.domain_metadata.items():
            domain_dir = os.path.join(self.corpus_dir, clean_domain)
            json_file_path = os.path.join(domain_dir, f"{clean_domain}.json")
            
            with open(json_file_path, 'w', encoding='utf-8') as json_file:
                json.dump(metadata_list, json_file, indent=4, ensure_ascii=False)
            
            spider.logger.info(f"Created metadata file: {json_file_path} with {len(metadata_list)} pages")
