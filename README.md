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

1. **Clone the repository**
   ```bash
   git clone https://github.com/guaran-ia/guarascrapper
   cd guarascrapper
   ```

2. **Create and activate a virtual environment** (recommended)
   ```bash
   python3 -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Clone the language identifier repository**
   ```bash
   # clone without blobs and without checking out files
   git clone --filter=blob:none --no-checkout https://github.com/guaran-ia/corpus.git
   cd corpus
   # initialize sparse-checkout and enable 'cone' mode
   git sparse-checkout init --cone
   # set the language identifier path
   git sparse-checkout set src/pipeline/language_identifier
   # check out the main branch
   git checkout main
   ```

---

## ▶️ Usage

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

---