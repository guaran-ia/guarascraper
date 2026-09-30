"""Offline regression checks: no live websites or language-model downloads."""

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

from scrapy.http import HtmlResponse
from scrapy import Request
from scrapy.crawler import Crawler
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.robotstxt import ProtegoRobotParser
from scrapy.settings import Settings
from scrapy.spiderloader import SpiderLoader
from scrapy.utils.misc import load_object
from scrapy.utils.project import get_project_settings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scraper.items import GuaraniWord
from scraper.pipelines import GuaraniScraperPipeline
from scraper.spider import GuaraniSpider
from scraper.utils import crawl_state


class ScraperTests(unittest.TestCase):
    def make_spider(self, crawler=None, **kwargs):
        # Replace only the external identifier; use the real Scrapy spider.
        module = ModuleType("corpus.src.pipeline.language_identifier.language_identifier")
        module.LanguageIdentifier = Mock(return_value=Mock())
        with patch.dict(sys.modules, {module.__name__: module}):
            if crawler is not None:
                return GuaraniSpider.from_crawler(crawler, **kwargs)
            return GuaraniSpider(**kwargs)

    def test_cli_help(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "cli.py"), "--help"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--crawl-domain", result.stdout)

    def test_cli_requires_one_input(self):
        for args in ([], ["--url", "https://example.org", "--csv", "urls.csv"]):
            with self.subTest(args=args):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "cli.py"), *args],
                    cwd=ROOT, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_cli_rejects_invalid_limits(self):
        for option, value in (
            ("--max-depth", "-1"), ("--max-pages", "1.5"),
            ("--timeout", "nan"), ("--timeout", "inf"),
            ("--download-delay", "-2"),
        ):
            with self.subTest(option=option, value=value):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "cli.py"), "--url", "https://example.org", option, value],
                    cwd=ROOT, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_cli_passes_crawl_limits_and_logs_effective_policy(self):
        import cli

        original_dir = os.getcwd()
        for options, expected in (
            ([], (3, 500, 600, 2)),
            (["--max-depth", "2", "--max-pages", "100", "--timeout", "300", "--download-delay", "5"],
             (2, 100, 300, 5)),
            (["--max-depth", "0", "--max-pages", "0", "--timeout", "0"], (0, 0, 0, 2)),
            (["--download-delay", "120"], (3, 500, 600, 120)),
        ):
            with self.subTest(options=options), \
                    patch.dict(os.environ, {}, clear=True), \
                    patch.object(sys, "argv", ["cli.py", "--url", "https://example.org", "--crawl-domain", *options]), \
                    patch.object(cli, "CrawlerProcess") as process, \
                    self.assertLogs("cli", level="INFO") as logs:
                cli.main()
                settings = process.call_args.args[0]
                actual = tuple(settings.getfloat(key) for key in (
                    "DEPTH_LIMIT", "CLOSESPIDER_PAGECOUNT", "CLOSESPIDER_TIMEOUT", "DOWNLOAD_DELAY",
                ))
                self.assertEqual(actual, expected)
                self.assertGreaterEqual(settings.getfloat("AUTOTHROTTLE_MAX_DELAY"), expected[3])
                process.return_value.crawl.assert_called_once_with(
                    GuaraniSpider, single_url="https://example.org", crawl_domain=True,
                )
                process.return_value.start.assert_called_once()
                self.assertIn("user_agent=GuaraScraper", logs.output[0])
                self.assertIn("robots_obey=True", logs.output[0])
                self.assertEqual(os.getcwd(), original_dir)

    def test_identity_matches_robot_rules(self):
        settings = Settings()
        settings.setmodule("scraper.settings")
        request = Request("https://example.org/private")
        middleware = UserAgentMiddleware(settings.get("USER_AGENT"))
        middleware.process_request(request, Mock())
        self.assertTrue(request.headers["User-Agent"].startswith(b"GuaraScraper "))
        parser = ProtegoRobotParser.from_crawler(None, b"""
User-agent: *
Allow: /

User-agent: GuaraScraper
Disallow: /private
""")
        agent = settings.get("ROBOTSTXT_USER_AGENT")
        self.assertFalse(parser.allowed(request.url, agent))
        self.assertTrue(parser.allowed("https://example.org/public", agent))

    def test_scrapy_configuration_discovers_spider_and_pipeline(self):
        original_dir = os.getcwd()
        try:
            os.chdir(ROOT / "src")
            with patch.dict(os.environ, {}, clear=True):
                settings = get_project_settings()
            loader = SpiderLoader(settings)
            self.assertIs(loader.load("guarani"), GuaraniSpider)
            pipelines = settings.getdict("ITEM_PIPELINES")
            self.assertEqual(len(pipelines), 1)
            self.assertIs(load_object(next(iter(pipelines))), GuaraniScraperPipeline)
        finally:
            os.chdir(original_dir)

    def test_single_page_does_not_follow_links(self):
        spider = self.make_spider(single_url="https://example.org/page")
        self.assertTrue(spider.single_page_only)
        self.assertEqual(spider.rules, ())
        with patch.object(spider, "_url_already_scraped", return_value=False):
            async def collect():
                return [request async for request in spider.start()]
            requests = asyncio.run(collect())
        self.assertEqual([request.url for request in requests], ["https://example.org/page"])
        self.assertEqual(requests[0].callback, spider.parse_item)

    def test_domain_mode_follows_links(self):
        spider = self.make_spider(single_url="https://example.org/page", crawl_domain=True)
        self.assertFalse(spider.single_page_only)
        self.assertEqual(spider.allowed_domains, ["example.org"])
        self.assertTrue(spider.rules[0].follow)

    def test_domain_startup_extracts_starting_page_and_follows_allowed_links(self):
        spider = self.make_spider(
            crawler=Crawler(GuaraniSpider, Settings()),
            single_url="https://example.org/page", crawl_domain=True,
        )
        spider.detector.identify_languages.return_value = {"languages": ["grn", 0.95]}

        async def collect_startup_output():
            requests = [request async for request in spider.start()]
            self.assertEqual(len(requests), 1)
            response = HtmlResponse(
                url=requests[0].url, request=requests[0], encoding="utf-8",
                body=('<html><body><p>Ñande ñe’ẽ iporã ha oikove.</p>'
                      '<a href="/next">Next</a>'
                      '<a href="https://other.example/">Offsite</a>'
                      '</body></html>').encode("utf-8"),
            )
            # Scrapy uses the spider's _parse when a start request has no callback.
            callback = requests[0].callback or spider._parse
            return [result async for result in callback(response)]

        with patch.object(spider, "_url_already_scraped", return_value=False):
            results = asyncio.run(collect_startup_output())
        items = [result for result in results if isinstance(result, GuaraniWord)]
        links = [result for result in results if isinstance(result, Request)]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["word"], "Ñande ñe’ẽ iporã ha oikove.")
        self.assertEqual(items[0]["url"], "https://example.org/page")
        self.assertEqual([request.url for request in links], ["https://example.org/next"])
        self.assertEqual(links[0].callback, spider._callback)
        spider.detector.identify_languages.assert_called_once()

    def test_extraction_excludes_scripts_and_non_guarani(self):
        spider = self.make_spider(single_url="https://example.org/page")
        spider.detector.identify_languages.side_effect = [
            {"languages": ["grn", 0.95]}, {"languages": ["spa", 0.99]},
        ]
        response = HtmlResponse(
            url="https://example.org/page", encoding="utf-8",
            body='<html><body><script>Ignore this script text entirely</script>'
                 '<style>Ignore this style text entirely</style>'
                 '<p>Ñande ñe’ẽ iporã ha oikove.</p><p>Este texto está en español.</p>'
                 '<p>Too short</p></body></html>'.encode("utf-8"),
        )
        with patch.object(spider, "_url_already_scraped", return_value=False):
            items = list(spider.parse_item(response))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["word"], "Ñande ñe’ẽ iporã ha oikove.")
        self.assertEqual(items[0]["url"], response.url)
        self.assertEqual(spider.detector.identify_languages.call_count, 2)

    def test_jsonl_merges_chunks_and_preserves_other_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            # Avoid creating or modifying project data during tests.
            with patch("scraper.pipelines.os.makedirs"):
                pipeline = GuaraniScraperPipeline()
            pipeline.corpus_dir = directory
            for url, text in (
                ("https://www.example.org/a", "Ñande ñe’ẽ"),
                ("https://www.example.org/b", "Ambue togue"),
                ("https://www.example.org/a", "ha ñande reko"),
            ):
                pipeline.process_item(GuaraniWord(url=url, word=text), None)
            output = Path(directory) / "download" / "example.org.jsonl"
            records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["text"], "Ñande ñe’ẽ\nha ñande reko")
            self.assertEqual(records[1]["text"], "Ambue togue")
            self.assertTrue(all(record["date"] for record in records))
            self.assertFalse(output.with_suffix(".jsonl.tmp").exists())

    def test_stored_state_checks_both_fineweb_lists_and_downloads(self):
        self.assertEqual(crawl_state.DATA_DIR, ROOT / "data")
        self.assertEqual(crawl_state.clean_domain("https://www.wikipedia.org/a"), "wikipedia.org")
        self.assertEqual(crawl_state.clean_domain("https://wood.example/a"), "wood.example")
        with tempfile.TemporaryDirectory() as directory, patch.object(crawl_state, "DATA_DIR", Path(directory)):
            fineweb = Path(directory) / "url_fineweb2"
            fineweb.mkdir()
            (fineweb / "example.org.csv").write_text(
                "url\nhttps://example.org/in-domain\n", encoding="utf-8",
            )
            (fineweb / "others_url_fineweb2.csv").write_text(
                "url\nhttps://example.org/in-fallback\nhttps://wood.example/known\n", encoding="utf-8",
            )
            spider = self.make_spider(single_url="https://example.org/new")
            self.assertTrue(spider._url_already_scraped("https://example.org/in-domain"))
            self.assertTrue(spider._url_already_scraped("https://example.org/in-fallback"))
            self.assertTrue(spider._url_already_scraped("https://wood.example/known"))
            self.assertFalse(spider._url_already_scraped("https://example.org/new"))
            self.assertFalse(spider._url_already_scraped("https://missing.example/new"))
            downloads = Path(directory) / "download"
            downloads.mkdir()
            (downloads / "example.org.jsonl").write_text(
                'not json\n[]\n{"url": null}\n{"url": "not-a-url"}\n'
                + json.dumps({"url": "https://example.org/new?a=1&b=2", "text": "saved"}) + "\n",
                encoding="utf-8",
            )
            self.assertTrue(spider._url_already_scraped("https://example.org/new?b=2&a=1#fragment"))
            self.assertFalse(spider._url_already_scraped("https://example.org/new?a=2&b=2"))

    def test_repeated_runs_do_not_append_existing_page_text(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(crawl_state, "DATA_DIR", Path(directory)):
            url = "https://www.wood.example/page"
            pipeline = GuaraniScraperPipeline()
            for text in ("Ñande ñe’ẽ", "ha ñande reko"):
                pipeline.process_item(GuaraniWord(url=url, word=text), None)
            output = Path(directory) / "download" / "wood.example.jsonl"
            original = output.read_bytes()

            for domain_mode in (False, True):
                spider = self.make_spider(single_url=url, crawl_domain=domain_mode)
                async def collect():
                    return [request async for request in spider.start()]
                self.assertEqual(asyncio.run(collect()), [])
                response = HtmlResponse(url=url, body=b"<body><p>Some new page text here</p></body>")
                self.assertEqual(list(spider.parse_item(response)), [])
                spider.detector.identify_languages.assert_not_called()

            # The pipeline independently protects old records if an item slips through.
            second_pipeline = GuaraniScraperPipeline()
            second_pipeline.process_item(GuaraniWord(url=url, word="duplicate content"), None)
            self.assertEqual(output.read_bytes(), original)
            second_pipeline.process_item(GuaraniWord(url="https://www.wood.example/new", word="new page"), None)
            records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["text"], "Ñande ñe’ẽ\nha ñande reko")

    def test_domain_rules_do_not_schedule_known_links(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(crawl_state, "DATA_DIR", Path(directory)):
            fineweb = Path(directory) / "url_fineweb2"
            fineweb.mkdir()
            (fineweb / "example.org.csv").write_text("url\nhttps://example.org/known\n", encoding="utf-8")
            spider = self.make_spider(
                crawler=Crawler(GuaraniSpider, Settings()),
                single_url="https://example.org/start", crawl_domain=True,
            )
            response = HtmlResponse(
                url="https://example.org/start", encoding="utf-8",
                body=b'<body><a href="/known">Known</a><a href="/new">New</a></body>',
            )
            async def collect():
                return [result async for result in spider._parse(response)]
            links = [result.url for result in asyncio.run(collect()) if isinstance(result, Request)]
            self.assertEqual(links, ["https://example.org/new"])


if __name__ == "__main__":
    unittest.main()
