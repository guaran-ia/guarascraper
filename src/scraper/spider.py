import csv
from urllib.parse import urlparse
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy import Request
# from ..utils.lang_detector import GuaraniDetector
from .items import GuaraniWord
from .utils import crawl_state


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
        from corpus.src.pipeline.language_identifier.language_identifier import LanguageIdentifier

        self.detector = LanguageIdentifier(glotlid=True, fasttext=True, openlid=True)
        self._fineweb_urls = {}



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
                    process_request="skip_known_request",
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
        # Exclude pages listed in FineWeb2 or our downloaded JSONL output.
        if getattr(self, "single_page_only", False):
            for url in getattr(self, "start_urls", []):
                
                if self._url_already_scraped(url):
                    self.logger.info("Skipping known URL: %s", url)
                    continue  
                yield Request(url, callback=self.parse_item, dont_filter=True)
        else:
            async for req in super().start():
                if not self._url_already_scraped(req.url):
                    yield req
                else:
                    self.logger.info("Skipping known URL: %s", req.url)

    def skip_known_request(self, request, response):
        """Exclude known pages before rule-based downloads are scheduled."""
        if self._url_already_scraped(request.url):
            self.logger.info("Skipping known URL: %s", request.url)
            return None
        return request

    def parse_start_url(self, response, **kwargs):
        """Extract the starting page while CrawlSpider handles link following."""
        yield from self.parse_item(response)

    def _url_already_scraped(self, url: str) -> bool:
        """Check both FineWeb2 URL lists and current downloaded JSONL output."""
        try:
            key = crawl_state.url_key(url)
            domain = crawl_state.clean_domain(url)
            if domain not in self._fineweb_urls:
                folder = crawl_state.DATA_DIR / "url_fineweb2"
                self._fineweb_urls[domain] = (
                    crawl_state.read_url_keys(folder / f"{domain}.csv", csv_file=True)
                    | crawl_state.read_url_keys(folder / "others_url_fineweb2.csv", csv_file=True)
                )
            return (key in self._fineweb_urls[domain]
                    or key in crawl_state.read_url_keys(crawl_state.download_path(url)))
        except (OSError, ValueError) as e:
            self.logger.warning("Error checking stored URL %s: %s", url, e)
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
        # Recheck state in case this URL was saved after the request was scheduled.
        try:
            if self._url_already_scraped(response.url):
                self.logger.info("parse_item: skipping known response %s", response.url)
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
    
