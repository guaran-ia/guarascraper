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
- follows internal links in a controlled manner  
- downloads HTML pages  
- extracts relevant textual content  
- stores results in a structured format  

---

## 🤖 User-Agent

GuaraScraper uses the following User-Agent for HTTP requests:

```
Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36
```

This User-Agent is defined in the scraper configuration and can be modified if needed.

---

## 🛡️ robots.txt

GuaraScraper respects the `robots.txt` protocol using Scrapy’s native support.

Configuration:

```
ROBOTSTXT_OBEY = True
```

This ensures that the crawler respects disallowed paths and directives such as `Crawl-delay`.

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
- Python 3.12+
- pip (Python package manager)

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
   is not included in this repository. The identifier may require model assets
   or additional packages; follow any setup instructions in that dependency.

5. **(Optional) Install processor dependencies**

   If you plan to normalize and report on downloaded data, install the separate
   processor dependencies as well:

   ```bash
   python -m pip install -r src/processor/requirements.txt
   ```

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

### 2️⃣ Scrape an entire domain
Scrapes the initial URL and traverses the entire domain, following internal links in a controlled manner:

```
python3 cli.py --url https://guaranimeme.blogspot.com --crawl-domain
```

### 3️⃣ Scrape a set of pages from a CSV file
Scrapes only the URLs listed in a CSV file, without crawling full domains:

```
python3 cli.py --csv data/web_sources.csv
```

### 4️⃣ Scrape a set of domains from a CSV file
Scrapes all domains defined in the CSV file, fully crawling each site:

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

## Automated checks

GitHub Actions runs offline checks on Python 3.12 for pushes and pull requests:
dependency consistency, source compilation, CLI startup, and regression tests
for Scrapy discovery, crawl modes, text extraction, and JSONL output.

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
live websites, or validate model accuracy or the processor's runtime setup.

---
