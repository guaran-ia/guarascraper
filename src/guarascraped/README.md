# Procedure applied to data obtained through web scraping🌐📚

This document describes the processing procedure applied to data obtained through web scraping, including metadata normalization, language identification, word and character counting, and statistics generation.

------------------------------------------------------------------------

## 🧩 Processing Pipeline (Normalization + Report Generation)

The raw scraping output was normalized and analyzed using a processing methodology implemented in  
[existing-guarani-corpora](https://github.com/guaran-ia/existing-guarani-corpora).

The processing pipeline performs the following steps:

- **Document-level metadata normalization:** ensures that all documents have a consistent structure, including fields such as **source**, **url**, **text**, and other relevant metadata.  
- **Character and word counts:** calculated using Python’s `split()` and spaCy.  
- **Language identification and scoring:** each document is analyzed with the [Language Identifier Tool](https://github.com/guaran-ia/corpus/tree/main/src/pipeline/language_identifier) to detect its language and compute a `language_score` representing how confidently the model identifies Guaraní words in the document.
- **Consistent `.jsonl` format:** ensures all documents are saved in a standardized structure.  
- **Aggregated dataset statistics:** provides overall summaries, including the total number of documents, total words, the average proportion of Guaraní words, among others.

All processed outputs are stored in:

```
data/processed/
```

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
```
data/processed/all_domains_report.json.
```

- **Total number of documents:** 46,152
- **Average language score:** 0.7805489521634437
- **Average number of words using `split()`:** 179.2303692147686
- **Average number of words using `spacy` with punctuation:** 214.09897729242502
- **Average number of words using `spacy` without punctuation:** 177.9657869648119
- **Total number of words using `split()`:** 8,271,840
- **Total number of words using `spacy` with punctuation:** 9,881,096
- **Total number of words using `spacy` without punctuation:** 8,213,477
- **Average number of characters:** 1,239.9789824926331
- **Total number of characters:** 57,227,510


------------------------------------------------------------------------