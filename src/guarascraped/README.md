# Procedure applied to data obtained through web scraping🌐📚

This document describes the processing procedure applied to data obtained through web scraping, including metadata normalization, language identification, word and character counting, and statistics generation.

------------------------------------------------------------------------

## 🧩 Processing Pipeline (Normalization + Report Generation)

The raw scraping output was **normalized and analyzed** using a processing
pipeline based on the methodology of the  
[**Existing Guarani Corpora**](https://github.com/guaran-ia/existing-guarani-corpora) project.

The processing pipeline includes:

- document-level metadata normalization
- character and word counts using `split()` and spaCy
- language identification and scoring
- consistent `.jsonl` output format
- generation of aggregated dataset statistics

The processed outputs are stored in:

```
data/processed/
```

Additionally, the **Language Identifier Tool** from:  
https://github.com/guaran-ia/corpus/tree/main/src/pipeline/language_identifier  
was used to compute the `language_score` for each document.

------------------------------------------------------------------------

## ⚙️ Script Used

The normalization and reporting were performed using:

```
src/guarascraped/formart_data.py
```

This script:

1. Loads all `.jsonl` files from `data/download/`
2. Normalizes fields following *Existing Guarani Corpora* conventions
3. Applies the Language Identifier Tool
4. Computes word counts (split/spaCy), character counts, and language scores
5. Aggregates global statistics
6. Writes the processed dataset and a summary report

------------------------------------------------------------------------

## ▶️ How to Run the Script

From the project root:

```bash
source guarascraper-venv/bin/activate
python3 -m src.guarascraped.formart_data
```

All dependencies (spaCy models, language identifier models, etc.) must be
installed beforehand.

------------------------------------------------------------------------

## 📁 Downloaded Data

The **raw scraping output** consists of multiple `.jsonl` files,
one per domain, stored in:

```
data/download/
```

Each file contains document-level entries such as:

```json
{
  "text": "",
  "date": "",
  "url": ""
}
```

------------------------------------------------------------------------

## 📂 Output Files

### ✅ 1. Normalized Dataset

```
data/processed/all_domains.jsonl
```

### ✅ 2. Global Report

```
data/processed/all_domains_report.json
```


------------------------------------------------------------------------

## 📊 General Dataset Statistics

All statistics below are derived from  
`data/processed/all_domains_report.json`.

### 📌 Documents

- **Total extracted documents:** 46,152

### 📝 Words

- **Total words (`split()`):** 8,271,840
- **Total words (spaCy with punctuation):** 9,881,096
- **Total words (spaCy without punctuation):** 8,213,477

- **Average per document (`split()`):** 179.23
- **Average per document (spaCy with punctuation):** 214.10
- **Average per document (spaCy without punctuation):** 177.97

### 🔤 Characters

- **Total characters:** 57,227,510
- **Average per document:** 1,239.98

### 🏳️ Language

- **Total language score:** 36,023.90

------------------------------------------------------------------------