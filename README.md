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

---

# Installation

## Prerequisites
- Python 3.12 (the CI-tested version; newer versions are not yet verified)
- pip (Python package manager)

### Dependency sets

| Component | Requirements | When needed |
| --- | --- | --- |
| Scraper | `requirements.txt` | CLI and Scrapy crawling |
| Processor | `src/processor/requirements.txt` | Normalization and report generation; independent of Scrapy |
| Language identifier | `corpus/src/pipeline/language_identifier/requirements.txt` | Shared runtime dependency for both crawling and processing |
| Offline scraper checks | `requirements-ci.txt` | Includes the scraper requirements; tests use standard-library `unittest` |
| Legacy detector | `src/scraper/utils/requirements-legacy.txt` | Only for manually using the old `GuaraniDetector`; not used by either active component |

These files declare direct dependencies and required compatibility packages,
with pinned versions for this project's components. They are not generated locks
of all transitive dependencies; pip
resolves those dependencies during installation. For a reproducible experiment,
record the external `corpus` commit (`git -C corpus rev-parse HEAD`) and the
resolved environment (`python -m pip freeze`) alongside the run outputs.

Offline scraper checks run on Linux in GitHub Actions; they have also been run
locally on macOS. Full crawling and processing additionally depend on the
external identifier and its models. Its FastText backend may require a C++
compiler and Python development headers if a suitable wheel is unavailable.
Legacy PyICU/Polyglot dependencies are optional and require their own native
library setup; they are not prerequisites for the active scraper or processor.

The optional legacy detector also expects the downloaded FastText model at
`src/scraper/utils/lang_model/lid.176.bin`. That exact asset is ignored by Git
and must be supplied separately to use the legacy detector. The active
components use the external identifier's model setup described below.

## Setup Instructions

Run these commands from a terminal. Replace `<repository-url>` with this repository's Git URL.

1. **Clone the repository**
   ```bash
   git clone <repository-url> guarascraper
   cd guarascraper
   ```

2. **Create and activate a virtual environment** (recommended)
   ```bash
   python3 -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install scraper dependencies**
   ```bash
   python -m pip install -r requirements.txt
   ```

4. **Fetch the language identifier dependency**

   The scraper and processor import the language identifier from the Guaran-IA
   `corpus` repository. Clone it into the project root and check out only the
   required source directory:

   ```bash
   git clone --filter=blob:none --sparse https://github.com/guaran-ia/corpus.git corpus
   git -C corpus sparse-checkout set src/pipeline/language_identifier
   ```

   Keep the `corpus/` directory beside `cli.py`; it is a runtime dependency and
   is not included in this repository. Install its requirements into the same
   virtual environment:

   ```bash
   python -m pip install -r corpus/src/pipeline/language_identifier/requirements.txt
   ```

   Follow the identifier's README for model setup. GlotLID and FastText models
   download on first use; OpenLID requires separate installation into the
   identifier's model directory. These assets are required for actual crawling
   and processing, but not for `--help` or offline scraper tests.

5. **(Optional) Install processor dependencies**

   If you plan to normalize and report on downloaded data, install the separate
   processor dependencies as well:

   ```bash
   python -m pip install -r src/processor/requirements.txt
   ```

   For a processor-only environment, install just the processor and external
   identifier requirements; skip step 3. See [processor setup](src/processor/README.md).

6. **Check the command-line entry point**

   ```bash
   python cli.py --help
   ```

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

To run these checks locally in an activated virtual environment:

```bash
python -m pip install -r requirements-ci.txt
python -m pip check
python -m compileall -q cli.py src
python cli.py --help
python -m unittest discover -s tests -v
```

The CI dependency set covers offline scraper checks. Tests replace the external
language identifier with a fake detector; they do not download models, crawl
live websites, or validate model accuracy or end-to-end processing with the
external language identifier.

---
