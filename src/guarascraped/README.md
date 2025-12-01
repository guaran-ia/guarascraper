# Guarani Web Scraping Results 🌐📚

This document summarizes the **raw results of the web scraping performed
on websites** that potentially contain Guarani-language text. The
extracted data represents the unprocessed content obtained from each
domain.

------------------------------------------------------------------------

## 📁 Dataset Overview

The scraping process generated multiple `.jsonl` files, one for each
domain, stored at:

    data/download/

Each `.jsonl` file contains the documents extracted from that site, with
objects such as:

``` json
{
  "text": "",
  "date": "",
  "url": ""
}
```

------------------------------------------------------------------------

## 📊 General Dataset Statistics

### 📌 Documents

-   **Total extracted documents:** 61167

### 📝 Words

-   **Total words (`split()`):** 10329420

-   **Total words (spaCy with punctuation):** 12165646

-   **Total words (spaCy without punctuation):** 10236204

-   **Average per document (`split()`):** 168.87

-   **Average per document (spaCy with punctuation):** 198.89

-   **Average per document (spaCy without punctuation):** 167.35

### 🔤 Characters

-   **Total characters:** 69,135,249
-   **Average per document:** 1,130.27

### 🏳️ Language

-   **Total language score:** 47,486.35
-   **Average language score:** 0.7763392929361872

------------------------------------------------------------------------

## 🧩 Processing Pipeline (Normalization + Report Generation)

The script used to normalize documents and generate the final dataset
statistics was **based on the processing pipeline of the**\
[**Existing Guarani Corpora
repository**](https://github.com/guaran-ia/existing-guarani-corpora).

The normalization follows the same structure and conventions:

-   document-level metadata
-   character and word counts using `split()` and spaCy
-   language identification
-   consistent `.jsonl` output format

Additionally, the **Language Identifier Tool** from:\
https://github.com/guaran-ia/corpus/tree/main/src/pipeline/language_identifier\
was used to compute the language score (`language_score`) for each
document extracted from the websites.

------------------------------------------------------------------------

## ⚙️ Script Used

The scraping results were processed using the normalization script:

    src/guarascraped/formart_data.py

This script:

1.  Loads all `.jsonl` files from `data/download/`
2.  Normalizes fields according to *Existing Guarani Corpora*
3.  Applies the Language Identifier Tool
4.  Counts words (split/spacy), characters, and computes language scores
5.  Generates summary statistics
6.  Saves the processed documents and a report file

------------------------------------------------------------------------

## ▶️ How to Run the Script

From the project root:

``` bash
source guarascraper-venv/bin/activate
python3 -m src.guarascraped.formart_data
```

Dependencies (spaCy, language identifier models, etc.) must be installed
beforehand.

------------------------------------------------------------------------

## 📂 Output Files

### ✅ 1. Normalized Dataset

    data/processed/all_domains.jsonl

### ✅ 2. Global Report

    data/processed/all_domains_report.json

------------------------------------------------------------------------

## 📝 Note

This dataset contains **only the raw scraping output**. It may include
text in Guarani, Spanish, or other languages, as well as duplicates or
low-content pages.\
The normalization and statistics generation were performed using a
pipeline inspired by *Existing Guarani Corpora* and leveraging the
**Language Identifier Tool** to measure Guarani content across the
scraped pages.
