"""Shared paths and URL identity for corpus exclusions and downloaded pages."""

import csv
import json
from pathlib import Path

from furl import furl

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def clean_domain(url):
    """Remove only an exact www. prefix, retaining the rest of the hostname."""
    return furl(url).host.lower().removeprefix("www.")


def url_key(url):
    """Match host, path, and query; ignore scheme/fragment as before."""
    parsed = furl(url)
    if not parsed.host:
        raise ValueError("URL has no hostname")
    return (parsed.host.lower(), str(parsed.path) or "/",
            tuple(sorted(parsed.query.params.allitems(),
                         key=lambda pair: (pair[0], pair[1] is not None, pair[1] or ""))))


def download_path(url, data_dir=None):
    root = DATA_DIR if data_dir is None else Path(data_dir)
    return root / "download" / f"{clean_domain(url)}.jsonl"


def read_url_keys(path, *, csv_file=False):
    """Read URL identities, skipping malformed records and absent files."""
    keys = set()
    try:
        with Path(path).open(encoding="utf-8-sig") as stream:
            records = csv.DictReader(stream) if csv_file else stream
            for record in records:
                try:
                    obj = record if csv_file else json.loads(record)
                    url = obj.get("url") if isinstance(obj, dict) else None
                    if isinstance(url, str) and url.strip():
                        keys.add(url_key(url))
                except (ValueError, TypeError):
                    continue
    except FileNotFoundError:
        pass
    return keys
