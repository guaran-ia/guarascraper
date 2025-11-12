import csv
from urllib import response
from urllib.parse import urlparse
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy import Request
# from ..utils.lang_detector import GuaraniDetector
from  corpus.src.pipeline.language_identifier.language_identifier import LanguageIdentifier

from ..items import GuaraniWord
from furl import furl
import os
import json


class GuaraniSpider(CrawlSpider):
    """
    Spider for crawling websites and extracting Guarani words.

    This spider crawls websites specified in a CSV file and extracts
    text content that is detected as being in the Guarani language.
    """

    name = "guarani"

    def __init__(self, csv_file=None, single_url=None, *args, **kwargs):
        """
        Initialize the GuaraniSpider with either a CSV file or a single URL.

        Args:
            csv_file (str): Path to CSV file with URLs to crawl
            single_url (str): Single URL to crawl
            *args, **kwargs: Additional arguments passed to CrawlSpider
        """
        # pop crawl_domain flag (passed from CLI) - default False
        crawl_domain = kwargs.pop("crawl_domain", False)

        super(GuaraniSpider, self).__init__(*args, **kwargs)
        self.detector = LanguageIdentifier(glotlid=True, fasttext=True, openlid=True)



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

        # Handle single URL input
        elif single_url:
            self.start_urls = [single_url]
            domain = urlparse(single_url).netloc
            self.allowed_domains = [domain]

            print(f"DEBUG: Single URL mode - crawling {single_url}")
            print(f"DEBUG: Allowed domain: {domain}")

        else:
            raise ValueError("Either csv_file or single_url must be provided")

        # Configure rules - follow links only when crawling domain
        # If we have either a single URL or a CSV and crawl_domain is False,
        # operate in single-page mode (do not follow links).
        if (single_url or csv_file) and not crawl_domain:
            # single-page mode: do not follow links
            self.rules = ()
            self.single_page_only = True
        else:
            self.rules = (
                Rule(
                    LinkExtractor(allow_domains=self.allowed_domains),
                    callback="parse_item",
                    follow=True,
                ),
            )
            # self.rules = (
            #     Rule(
            #         # Only follow links whose path contains /gn/ (efficient: avoids downloads outside /gn/)
            #         LinkExtractor(allow=(r'/gn(/|$)',), allow_domains=self.allowed_domains),
            #         callback="parse_item",
            #         follow=True,
            #     ),
            # )
            self.single_page_only = False

        super()._compile_rules()

    async def start(self):
        """Async start for Scrapy 2.13+.

        - If single-page mode is enabled, schedule only the provided start_urls.
        - Otherwise, delegate to the parent's async start(), which will
          produce the standard initial requests and enable rule-based crawling.
        """
        self.logger.debug("start: single_page_only=%s start_urls=%s", getattr(self, "single_page_only", False), getattr(self, "start_urls", None))
        # Before scheduling requests, check if the URL has already been scraped
        # by looking for a domain-specific jsonl file under the project's data/ directory.
        if getattr(self, "single_page_only", False):
            for url in getattr(self, "start_urls", []):
                
                if self._url_already_scraped(url):
                    self.logger.info("Skipping already-scraped URL: %s", url)
                    continue  
                yield Request(url, callback=self.parse_item, dont_filter=True)
        else:
            async for req in super().start():
                yield req

    def _domain_csv_path(self, domain: str) -> str | None:
        """Return the expected jsonl path for a domain inside the top-level data/ dir.

        Normalizes 'www.' prefix away. Example: 'abc.com.py' -> 'data/abc.com/abc.com.csv'
        """
        domain = domain.lower().lstrip("www.")
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        data_dir = os.path.join(workspace_root, "data")

        # First check the url_fineweb2 folder where we store domain jsonl files like abc.com.py.jsonl
        fineweb_path = os.path.join(data_dir, "url_fineweb2", f"{domain}.csv")
        if os.path.exists(fineweb_path):
            return fineweb_path

        # self.logger.info(
        #     "No se encontró archivo CSV para el dominio '%s' en la ruta %s",
        #     domain,
        #     fineweb_path,
        # )
        return None

    def _url_already_scraped(self, url: str) -> bool:
        """Check whether a URL is already present in the domain jsonl file.

        Returns True if the domain file exists and contains a record whose 'url'
        field equals the provided URL. If the file doesn't exist, returns False.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower().lstrip("www.")
        path = self._domain_csv_path(domain)
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

        if not path or not os.path.exists(path):
            # If the domain-specific CSV file path is missing or doesn't exist,
            # try to use the fallback file "others_url_fineweb2.csv" instead.
            fallback_path = "data/url_fineweb2/others_url_fineweb2.csv"
            data_dir = os.path.join(workspace_root, fallback_path)

            # Check if the fallback file exists
            if os.path.exists(data_dir):
                # If it exists, return its path  
                path = data_dir
            else:
                # If neither the domain CSV nor the fallback file exist, return False
                return False


        try:
            with open(path, "r", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)  # usa la cabecera como keys
                for row in reader:
                    url1 = furl(url)
                    url2 = furl(row.get("url"))
                    if (url1.host, url1.path, url1.query.params) == (url2.host, url2.path, url2.query.params):
                        return True
            return False
        except Exception as e:
            # Si hay error de IO o formato, no lo tratamos como ya scrapeado
            self.logger.warning(f"Error leyendo {path}: {e}")
            return False


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
        # If this URL was already scraped (exists in domain jsonl), skip processing
        try:
            if self._url_already_scraped(response.url):
                self.logger.info("parse_item: skipping already-scraped response %s", response.url)
                return
        except Exception:
            # If any error occurs while checking, continue processing as before
            self.logger.debug("parse_item: error checking scraped state for %s", response.url, exc_info=True)

        text_chunks = response.xpath('''
            //body//*[not(
                self::script or
                self::style or
                self::noscript or
                self::svg or
                self::meta or
                self::link or
                self::iframe or
                self::head or
                self::title
            )]//text()[normalize-space() and
                not(ancestor::script) and
                not(ancestor::style) and
                not(ancestor::noscript) and
                not(ancestor::svg) and
                not(ancestor::iframe)
            ]
        ''').getall()
        
        words_found = 0

        for chunk in text_chunks:
            # chunk = chunk.strip()
            chunk = chunk.replace('\n', ' ').replace('\r', ' ').strip()
            if len(chunk.split()) < 4 or not chunk:  # Skip short chunks
                continue
            # yield GuaraniWord(
            #     word=chunk,
            #     url=response.url,
            #     domain=urlparse(response.url).netloc,
            # )

            # Check if this chunk is Guarani
            result = self.detector.identify_languages(chunk, k=1, raw_output=False)
            # lang_code, confidence = result['languages'][0]  # <--- usar [0]

            if result['languages'][0] == 'grn':
                yield GuaraniWord(
                    word=chunk,
                    url=response.url,
                    domain=urlparse(response.url).netloc,
                )
                print("#"*80)
                print(f"DEBUG: Found Guarani chunk with confidence {result['languages'][1]}: '{chunk}'")

            # if self.detector.is_guarani(chunk):
            #     yield GuaraniWord(
            #         word=chunk,
            #         url=response.url,
            #         domain=urlparse(response.url).netloc,
            #     )
            #     print("DEBUG: Found Guarani chunk")
                # Now extract words from this Guarani chunk
                # words = [w.strip() for w in chunk.split() if w.strip()]
                # for word in words:
                #     # Additional filtering if needed
                #     if len(word) > 2:  # Skip very short words
                #         words_found += 1
                #         yield GuaraniWord(
                #             word=word,
                #             url=response.url,
                #             domain=urlparse(response.url).netloc,
                #         )

            # else:
            #     # Check individual words using NLTK directly
                


            #     words = [w.strip() for w in chunk.split() if w.strip()]
            #     for word in words:
            #         if len(word) > 2 and self.detector._nltk_guarani_check(word):  # Usar NLTK directamente
            #             words_found += 1
            #             print(f"DEBUG: Found individual Guarani word: '{word}'")
            #     if words_found >= len(words) * 0.6:
            #         print(f"DEBUG: Chunk majority Guarani (>60%), saving: '{chunk}'")
            #         yield GuaraniWord(
            #             word=chunk,  # guardamos todo el chunk
            #             url=response.url,
            #             domain=urlparse(response.url).netloc,
            #         )
        
        if words_found > 0:
            print(f"DEBUG: Total words found in chunk: {words_found}")
    
