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
from scrapy.spiderloader import SpiderLoader
from scrapy.utils.misc import load_object
from scrapy.utils.project import get_project_settings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scraper.items import GuaraniWord
from scraper.pipelines import GuaraniScraperPipeline
from scraper.spider import GuaraniSpider


class ScraperTests(unittest.TestCase):
    def make_spider(self, **kwargs):
        # Replace only the external identifier; use the real Scrapy spider.
        module = ModuleType("corpus.src.pipeline.language_identifier.language_identifier")
        module.LanguageIdentifier = Mock(return_value=Mock())
        with patch.dict(sys.modules, {module.__name__: module}):
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


if __name__ == "__main__":
    unittest.main()
