import csv
from urllib.parse import urlparse
import re
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from ..utils.lang_detector import GuaraniDetector
from ..items import GuaraniWord


class GuaraniSpider(CrawlSpider):
    """
    Spider for crawling websites and extracting Guarani words.

    This spider crawls websites specified in a CSV file and extracts
    text content that is detected as being in the Guarani language.
    """

    name = "guarani"

    def __init__(self, csv_file=None, *args, **kwargs):
        """
        Initialize the GuaraniSpider with a CSV file containing URLs to crawl.

        Args:
            csv_file (str): Path to CSV file with URLs to crawl
            *args, **kwargs: Additional arguments passed to CrawlSpider
        """
        super(GuaraniSpider, self).__init__(*args, **kwargs)
        self.detector = GuaraniDetector()

        # Read URLs from CSV
        if csv_file:
            with open(csv_file) as f:
                reader = csv.DictReader(f)
                urls = [row["url"] for row in reader]
                self.start_urls = urls
                
                # Extract allowed domains from start URLs
                self.allowed_domains = []
                for url in urls:
                    domain = urlparse(url).netloc
                    if domain not in self.allowed_domains:
                        self.allowed_domains.append(domain)

        # Configure rules - restrict to allowed domains
        self.rules = (
            Rule(
                LinkExtractor(allow_domains=self.allowed_domains), 
                callback="parse_item", 
                follow=True
            ),
        )

        super()._compile_rules()

    def parse_item(self, response):
        """
        Parse a web page and extract Guarani words.

        Extracts all visible text from the page by selecting text from
        paragraphs, headings, links, and other content elements. The text
        is then cleaned, normalized, and split into individual words.
        Each word is checked to determine if it's Guarani using the
        GuaraniDetector, and if identified as Guarani, it's yielded
        as a GuaraniWord item.

        Args:
            response (scrapy.http.Response): The HTTP response object
                containing the web page content

        Yields:
            GuaraniWord: Items containing Guarani words along with metadata
                         such as the source URL and domain
        """
        text_chunks = response.xpath(
            '//p//text() | //div[not(contains(@class, "nav"))]//text()'
        ).getall()

        for chunk in text_chunks:
            chunk = chunk.strip()
            if not chunk or len(chunk) < 100:  # Skip short chunks
                continue
            
            words_found = 0

            # Check if this chunk is Guarani
            if self.detector.is_guarani(chunk):
                print("DEBUG: Found Guarani chunk")
                # Now extract words from this Guarani chunk
                words = [w.strip() for w in chunk.split() if w.strip()]
                for word in words:
                    # Additional filtering if needed
                    if len(word) > 2:  # Skip very short words
                        words_found += 1
                        yield GuaraniWord(
                            word=word,
                            url=response.url,
                            domain=urlparse(response.url).netloc,
                        )

            else:
                # Method 2: Check individual words if chunk wasn't detected as Guarani
                words = [w.strip() for w in chunk.split() if w.strip()]
                for word in words:
                    if len(word) > 2 and self.is_guarani_word(word):
                        words_found += 1
                        print(f"DEBUG: Found individual Guarani word: '{word}'")
                        yield GuaraniWord(
                            word=word,
                            url=response.url,
                            domain=urlparse(response.url).netloc,
                        )
            
            if words_found > 0:
                print(f"DEBUG: Total words found in chunk: {words_found}")
    
    def is_guarani_word(self, word):
        """
        Simple word-level Guarani detection.
        
        Checks individual words for Guarani characteristics using
        simplified rules optimized for single words rather than
        text chunks.

        Args:
            word (str): Individual word to analyze

        Returns:
            bool: True if word appears to be Guarani
        """
        word = word.lower().strip()
        
        # Remove punctuation but preserve Guarani characters and apostrophes
        word = re.sub(r'[^\w\sñáéíóúãẽĩõũỹ\']', '', word)
        
        # Direct match with known Guarani words
        if word in self.detector.guarani_stopwords:
            return True
        
        # Has nasal vowels (very characteristic of Guarani)
        if re.search(r'[ãẽĩõũỹ]', word):
            return True
        
        # Has typical Guarani consonant clusters
        if re.search(r'(mb|nd|ng|ñ)', word):
            return True
        
        # Has typical Guarani morphemes (suffixes)
        if re.search(r'(kue|gua|va.e|rã|ngo|piko)$', word):
            return True