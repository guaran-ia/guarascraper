# 🕷️ GuaraScraper

**GuaraScraper** is an **automated web crawler** designed to traverse public websites and **extract textual content that potentially contains Guarani language**.  
The scraper is intended for **systematic data collection** to support linguistic corpus construction and subsequent analysis.

---

## 🧠 Overview

- **Type:** Web crawler / Data scraper  
- **Primary purpose:** Public web content collection  
- **Target language:** Guarani  
- **Implementation:** Python + Scrapy  
- **Output:** Structured text data (`.jsonl`)

---

## 🌐 Crawling behavior

GuaraScraper:
- accesses only publicly available web content  
- starts crawling from predefined URLs or domains  
- follows links within the input domains (including their subdomains) only
  when `--crawl-domain` is supplied
- downloads HTML pages  
- extracts relevant textual content  
- stores results in a structured format  

Domain crawling is bounded by default; it does not guarantee a complete copy of
a site. When a CSV supplies multiple domains, they share the same run-wide
page and time limits, and links between those allowed domains can be followed.
Pages are fetched before language identification, so requests are not restricted
to Guarani-language pages. JavaScript is not executed, cookies are disabled, and
automatic retries and HTTP/meta-refresh redirects are disabled.

### Default crawl policy

| Control | Default | CLI override |
| --- | --- | --- |
| Maximum link depth from a starting page (depth 0) | 3 | `--max-depth` |
| Response-count shutdown threshold, across all domains | 500 | `--max-pages` |
| Time before initiating shutdown after the spider opens | 600 seconds | `--timeout` |
| Minimum delay between requests to the same domain | 2 seconds | `--download-delay` |
| Concurrent requests per domain | 1 | Set in `src/scraper/settings.py` |
| Concurrent requests across all domains | 8 | Set in `src/scraper/settings.py` |

AutoThrottle starts with a 5-second delay, targets one concurrent request per
domain, and adapts to response latency with a default maximum delay of 60
seconds. The CLI raises that maximum if a larger download delay is requested.
Delay randomization is disabled so the configured download delay is a
floor. Page counts include responses even if no text is extracted, not the
number of saved records. The page and time limits initiate graceful shutdown;
already in-flight requests may finish, so neither is a strict final count or
wall-clock deadline. Limits also apply in single-page/CSV page-list mode.

For example, a smaller crawl with a slower request rate:

```bash
python cli.py --url https://guaranimeme.blogspot.com --crawl-domain \
  --max-depth 2 --max-pages 100 --timeout 300 --download-delay 5
```

Setting `--max-depth`, `--max-pages`, or `--timeout` to `0` disables that
individual limit. The effective identity, robots policy, limits, and throttling
settings are logged at startup to `logs/scraper_errors.log` and the console.
The file includes INFO-level policy messages despite its historical name.

HTTP caching is enabled in `src/.scrapy/httpcache/` with no expiration by
default. Cached responses can be reused on later runs, so a repeated crawl may
not fetch fresh content. Change `HTTPCACHE_ENABLED` or `HTTPCACHE_EXPIRATION_SECS`
in `src/scraper/settings.py` to adjust that behavior.

---

## 🤖 User-Agent

GuaraScraper uses the following User-Agent for HTTP requests:

```
GuaraScraper (+https://github.com/guaran-ia/guarascraper)
```

The project link provides identification and a contact route through GitHub
issues. `USER_AGENT` is defined in `src/scraper/settings.py`; operators can add
their own contact URL there while keeping the `GuaraScraper` product name.

---

## 🛡️ robots.txt

GuaraScraper respects the `robots.txt` protocol using Scrapy’s native support.

Configuration:

```
ROBOTSTXT_OBEY = True
ROBOTSTXT_USER_AGENT = "GuaraScraper"
```

Scrapy checks robots.txt access rules using the `GuaraScraper` product name,
falling back to wildcard rules when no matching group exists. Site operators
can block the crawler with:

```text
User-agent: GuaraScraper
Disallow: /
```

Scrapy's native robots middleware does **not** apply the `Crawl-delay` directive.
Request pacing is controlled by `DOWNLOAD_DELAY` and AutoThrottle; operators
should set `--download-delay` to meet a site's published pacing requirements.

---

## 📦 Data collection

Collected data is stored in `.jsonl` format under the following directory:

```
data/download/
└── domain-name.jsonl
```

Each record includes:
- extracted text  
- source URL  
- extraction date  

See [data formats and filtering](docs/data-format.md) for synthetic examples,
field definitions, timestamp conventions, confidence filtering, and limitations.

### Previously collected pages and FineWeb2 exclusions

Before scheduling a page, the scraper checks both:

* FineWeb2 URL lists in `data/url_fineweb2/<domain>.csv` and
  `data/url_fineweb2/others_url_fineweb2.csv`. Supply these optional lists with a
  `url` column. Both files are checked even when a domain-specific file exists.
* Previously saved page URLs in `data/download/<domain>.jsonl`.

Domain filenames remove only the exact `www.` prefix. URL matching uses the
hostname, path, and query parameters (independent of parameter order), ignoring
the scheme and fragment as in the previous FineWeb2 check. Different query
values remain distinct; `www.` and bare hostnames remain distinct URL identities
even though they share a domain output file.

Known pages are skipped in URL, CSV, and domain-crawl modes. Skipped pages are
not downloaded for link discovery, so a known starting page or intermediate
page cannot provide links to new pages. Supply unknown entry points when
continuing a crawl. FineWeb2 lists are loaded lazily and cached for the run;
downloaded JSONL state is checked again when responses are parsed.

Missing state files provide no exclusions, and malformed URL records are
ignored. The pipeline also preserves records that existed before it started
writing to each domain file, preventing later runs from appending duplicate
text. New chunks from the same page in the current run are still concatenated.

---

# Installation

## Prerequisites
- Python 3.12.7 for the reproduced environment (other Python versions are not verified)
- Git and a C++ compiler for building FastText when no wheel is available
- About 4.1 GB for the three models, plus space for Python packages and caches

### Dependency sets

| Component | Requirements | When needed |
| --- | --- | --- |
| Scraper | `requirements.txt` | CLI and Scrapy crawling |
| Processor | `src/processor/requirements.txt` | Normalization and report generation; independent of Scrapy |
| Language identifier | `requirements-identifier.txt` | Shared dependencies for the revision in `identifier.lock.json` |
| Full active runtime | `requirements-runtime.txt` | Includes scraper, processor, and identifier requirements |
| Build tools | `requirements-build.txt` | Pinned tools for the FastText source build |
| Offline scraper checks | `requirements-ci.txt` | Includes the scraper requirements; tests use standard-library `unittest` |
| Legacy detector | `src/scraper/utils/requirements-legacy.txt` | Only for manually using the old `GuaraniDetector`; not used by either active component |

Requirement files declare direct dependencies. Separately,
`constraints/python312.txt` pins the resolved runtime and build-tool versions.
Use `-c constraints/python312.txt` when installing a component or the full
runtime. These are version constraints, not a hash-locked wheel bundle.

The real-model scrape-to-processor check has been verified on CPython 3.12.7,
macOS arm64. Linux has CI workflows for offline checks and an on-demand
real-model integration run; Windows is not currently verified. FastText may
require Python development headers as well as a C++ compiler.
Legacy PyICU/Polyglot dependencies are optional and require their own native
library setup; they are not prerequisites for the active scraper or processor.

The optional legacy detector also expects the downloaded FastText model at
`src/scraper/utils/lang_model/lid.176.bin`. That exact asset is ignored by Git
and must be supplied separately to use the legacy detector. The active
components use the external identifier's model setup described below.

## Setup Instructions

Run these commands from a terminal.

1. **Clone the repository**
   ```bash
    git clone https://github.com/guaran-ia/guarascraper.git
   cd guarascraper
   ```

2. **Create and activate a virtual environment** (recommended)
   ```bash
    python3.12 -m venv venv
    source venv/bin/activate
   ```

3. **Install the tested build tools and runtime**
    ```bash
    python -m pip install -c constraints/python312.txt -r requirements-build.txt
    python -m pip install --no-build-isolation -c constraints/python312.txt -r requirements-runtime.txt
    python -m pip check
    ```

   `--no-build-isolation` ensures FastText uses the installed pinned build tools.
   The full runtime includes the optional processor. For scraper-only use,
   install `requirements.txt` and `requirements-identifier.txt` together using
   the same constraints and build options; see
   [component-only environments](docs/setup.md#component-only-environments).
   For processor-only use, see [processor setup](src/processor/README.md).

4. **Prepare the pinned identifier and models**

    ```bash
    python scripts/setup_identifier.py
    ```

   The script creates a sparse `corpus/` checkout at revision
   `d599a2e4ae065f8708c7b15aefc30c0832760d33`, downloads the three model artifacts
   at the revisions in `identifier.lock.json`, and checks their SHA-256 hashes.
   All models are prepared before runtime; the scraper and processor load the
   pinned cached artifacts without contacting Hugging Face. Upstream prediction
   and voting logic is retained; our loader overrides its model-loading methods.
   The OpenLID artifact comes from the pinned official `laurievb/OpenLID` model
   repository instead of the unversioned compressed download URL.

   An existing non-Git `corpus/` directory, a different revision, or modified
   identifier source is rejected rather than overwritten. See
   [troubleshooting](docs/setup.md#troubleshooting) for using another checkout
   location and model download recovery. Model files remain outside Git;
   their licenses are those of their respective model repositories.

5. **Check startup and the complete local flow**

    ```bash
    python cli.py --help
    python -m src.processor.formart_data --help
    python scripts/integration_check.py
    ```

   The integration check serves synthetic HTML on localhost, runs the real CLI
   in a fresh temporary source/output layout, processes the result using all
   three real models, and checks that a repeated crawl preserves the record.
   It does not use the project's data directories or contact live source sites.
   Full setup details and maintenance instructions are in [docs/setup.md](docs/setup.md).

---

## ▶️ Usage

Run the commands below from the repository root with the virtual environment
activated.

GuaraScraper can be executed in different ways depending on the desired scraping scope.

### 1️⃣ Scrape a single page
Scrapes only the specified URL, without following additional links:

```
python3 cli.py --url https://guaranimeme.blogspot.com
```

### 2️⃣ Crawl a domain
Starts at the specified URL and follows links within its domain, subject to
robots.txt and the configured crawl limits:

```
python3 cli.py --url https://guaranimeme.blogspot.com --crawl-domain
```

### 3️⃣ Scrape a set of pages from a CSV file
Scrapes only the URLs listed in a CSV file, without crawling full domains:

```
python3 cli.py --csv data/web_sources.csv
```

### 4️⃣ Scrape a set of domains from a CSV file
Follows links within domains defined in the CSV file, sharing the run's page
and time limits:

```
python3 cli.py --csv data/web_sources.csv --crawl-domain
```

### 📂 Data output

Extracted text is saved in the corresponding directory (e.g. `data/download/`) in structured `.jsonl` format, along with metadata such as the source URL and domain.

### Process downloaded data (optional)

After installing the processor dependencies, run the processor from the
repository root:

```bash
python -m src.processor.formart_data
```

To require a higher Guarani classification confidence:

```bash
python -m src.processor.formart_data --min-language-score 0.85
```

`--min-language-score` accepts values from `0` to `1` and defaults to `0.70`.
The boundary is inclusive, and the document must still be classified as `grn`.
This is model confidence, not a required percentage of Guarani words.

It reads `data/download/*.jsonl` and writes the normalized dataset and report
under `data/processed/`.

## Contributing and license

Contributions are submitted under the terms in [CONTRIBUTING.md](CONTRIBUTING.md).
The project source code is licensed under the [Apache License 2.0](LICENSE).
Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).
For vulnerability reports, follow the private reporting instructions in
[SECURITY.md](SECURITY.md). Bug reports and feature requests can be submitted
through [GitHub issues](https://github.com/guaran-ia/guarascraper/issues).

## Automated checks

GitHub Actions runs offline checks on Python 3.12 for pushes and pull requests:
dependency consistency, source compilation, CLI startup, and regression tests
for Scrapy discovery, crawl modes, text extraction, and JSONL output.
An independent processor job installs only the processor requirements and
checks module imports and blank-tokenizer initialization.
It also tests processor language filtering at the inclusive 0.70 confidence
boundary. Run these tests in a processor environment with
`python -m unittest discover -s tests/processor -v`.

To run these checks locally in an activated virtual environment:

```bash
python -m pip install -c constraints/python312.txt -r requirements-ci.txt
python -m pip check
python -m compileall -q cli.py src
python cli.py --help
python -m unittest discover -s tests -v
```

The default CI tests use a fake detector and do not download models or crawl
live websites. The separate **Real-model integration** workflow can be started
manually in GitHub Actions; it installs the constrained runtime, prepares and
verifies pinned models, and runs the localhost scrape-to-processor check.

---
