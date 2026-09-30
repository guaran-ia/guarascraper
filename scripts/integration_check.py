"""Exercise the real CLI and processor using all three pinned language models."""

import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.language_identifier import corpus_directory, identifier_config, verify_checkout


def main():
    directory = corpus_directory()
    config = identifier_config()
    verify_checkout(directory, config)
    requests = []

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.path, self.headers.get("User-Agent")))
            super().do_GET()

        def log_message(self, format, *args):
            pass

    handler = functools.partial(Handler, directory=str(ROOT / "tests" / "fixtures" / "integration"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="guarascraper-integration-") as temporary:
            workspace = Path(temporary)
            # Fresh source/output layout: never write to the user's dataset or docs.
            shutil.copytree(ROOT / "src", workspace / "src", ignore=shutil.ignore_patterns(
                "__pycache__", ".scrapy", "*.bin", "*.part",
            ))
            shutil.copy2(ROOT / "cli.py", workspace / "cli.py")
            shutil.copy2(ROOT / "identifier.lock.json", workspace / "identifier.lock.json")
            env = os.environ.copy()
            env["GUARASCRAPER_CORPUS_DIR"] = str(directory)
            env.pop("SCRAPY_SETTINGS_MODULE", None)
            env.pop("PYTHONPATH", None)

            def run(*args):
                result = subprocess.run(
                    [sys.executable, *args], cwd=workspace, env=env,
                    capture_output=True, text=True, timeout=300,
                )
                if result.returncode:
                    raise RuntimeError(result.stdout + result.stderr)
                return result

            url = f"http://127.0.0.1:{server.server_port}/index.html"
            crawl_args = ("cli.py", "--url", url, "--crawl-domain", "--max-pages", "10", "--timeout", "120")
            crawl = run(*crawl_args)
            raw_path = workspace / "data" / "download" / "127.0.0.1.jsonl"
            if not raw_path.exists():
                raise RuntimeError("Scraper produced no output:\n" + crawl.stdout + crawl.stderr)
            original = raw_path.read_bytes()
            raw = [json.loads(line) for line in original.decode("utf-8").splitlines()]
            assert len(raw) == 1 and raw[0]["url"] == url
            assert "Ñande ñe’ẽ guarani" in raw[0]["text"]
            assert "English control" not in raw[0]["text"]
            assert "script should" not in raw[0]["text"]
            assert raw[0]["date"]

            run("-m", "src.processor.formart_data", "--min-language-score", "0.70")
            processed = workspace / "data" / "processed"
            records = [json.loads(line) for line in (processed / "all_domains.jsonl").read_text(encoding="utf-8").splitlines()]
            report = json.loads((processed / "all_domains_report.json").read_text(encoding="utf-8"))
            assert len(records) == report["num_docs"] == 1
            document = records[0]
            assert document["language"] == "grn" and document["language_score"] >= 0.70
            assert document["text"] == " ".join(raw[0]["text"].split())
            assert document["num_chars"] == len(document["text"])
            assert document["num_words_split"] == len(document["text"].split())
            assert report["num_chars"] == document["num_chars"]

            fetched_pages = sum(path == "/index.html" for path, agent in requests)
            run(*crawl_args)
            assert raw_path.read_bytes() == original
            assert sum(path == "/index.html" for path, agent in requests) == fetched_pages == 1
            assert all(agent.startswith("GuaraScraper ") for path, agent in requests)
            print(f"PASS: real-model scrape → process → repeat-run check; confidence={document['language_score']:.6f}")
            print(f"Identifier revision: {config['revision']}")
            print("Model revisions: " + ", ".join(f"{name}={model['revision']}" for name, model in config["models"].items()))
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
