"""Processor filtering checks without external language models."""

import sys
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.processor.formart_data import identify_language
from src.processor import formart_data as processor


class LanguageFilteringTests(unittest.TestCase):
    def test_cli_threshold_validation(self):
        self.assertEqual(processor.parse_args([]).min_language_score, 0.70)
        for score in ("0", "0.6", "0.85", "1"):
            with self.subTest(score=score):
                self.assertEqual(processor.parse_args(["--min-language-score", score]).min_language_score, float(score))
        for score in ("-0.1", "1.1", "nan", "inf", "not-a-number"):
            with self.subTest(score=score), patch("sys.stderr"):
                with self.assertRaises(SystemExit) as error:
                    processor.parse_args(["--min-language-score", score])
                self.assertEqual(error.exception.code, 2)

    def test_cli_threshold_controls_retained_output(self):
        identifier = Mock()
        identifier.identify_languages.return_value = {
            "languages": ("grn", 0.80), "source": "glotlid", "voting": "agree",
        }
        for args, retained in (([], 1), (["--min-language-score", "0.9"], 0),
                               (["--min-language-score", "0.8"], 1)):
            with self.subTest(args=args), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                downloads = root / "data" / "download"
                downloads.mkdir(parents=True)
                (downloads / "example.org.jsonl").write_text(json.dumps({
                    "text": "Ñande ñe’ẽ iporã ha oikove.", "url": "https://example.org/page",
                }) + "\n", encoding="utf-8")
                with patch.object(processor, "create_identifier", return_value=identifier), \
                        patch.object(processor, "__file__", str(root / "src" / "processor" / "formart_data.py")), \
                        patch.object(processor, "finalize_report", side_effect=lambda report: report), \
                        patch.object(processor, "tqdm"), patch("builtins.print"):
                    processor.main(args)
                output = root / "data" / "processed"
                self.assertEqual(len((output / "all_domains.jsonl").read_text().splitlines()), retained)
                report = json.loads((output / "all_domains_report.json").read_text())
                self.assertEqual(report["num_docs"], retained)

    def test_guarani_confidence_boundary(self):
        for score, accepted in ((0.699999, False), (0.70, True), (0.92, True)):
            with self.subTest(score=score):
                identifier = Mock()
                identifier.identify_languages.return_value = {
                    "languages": ("grn", score),
                    "source": "glotlid", "voting": "agree_glotlib_fasttext_openlid",
                }
                result = identify_language("  Ñande ñe’ẽ\niporã ha oikove.  ", identifier, "grn")
                if accepted:
                    self.assertEqual(result["score"], score)
                    self.assertEqual(result["lang"], "grn")
                    self.assertEqual(result["source_score"], "glotlid")
                else:
                    self.assertIsNone(result)
                identifier.identify_languages.assert_called_once_with(
                    "Ñande ñe’ẽ iporã ha oikove.", k=1, raw_output=False,
                )

    def test_high_confidence_other_language_is_rejected(self):
        identifier = Mock()
        identifier.identify_languages.return_value = {"languages": ("spa", 0.99)}
        self.assertIsNone(identify_language("Este texto está en español.", identifier, "grn"))

    def test_empty_text_does_not_invoke_identifier(self):
        identifier = Mock()
        self.assertIsNone(identify_language(" \n\t ", identifier, "grn"))
        identifier.identify_languages.assert_not_called()


if __name__ == "__main__":
    unittest.main()
