# Procedure applied to data obtained through web scraping🌐📚

This document describes the processing procedure applied to data obtained through web scraping, including metadata normalization, language identification, word and character counting, and statistics generation.

------------------------------------------------------------------------

## 🧩 Processing Pipeline (Normalization + Report Generation)

The raw scraping output was normalized and analyzed using a processing methodology implemented in  
[existing-guarani-corpora](https://github.com/guaran-ia/existing-guarani-corpora).

The processing pipeline performs the following steps:

- **Document-level metadata normalization:** ensures that all documents have a consistent structure, including fields such as **source**, **url**, **text**, and other relevant metadata.  
- **Character and word counts:** calculated using Python’s `split()` and spaCy.  
- **Language identification and scoring:** each document is analyzed with the [Language Identifier Tool](https://github.com/guaran-ia/corpus/tree/main/src/pipeline/language_identifier). Only documents classified as `grn` with confidence at least the selected threshold (**0.70** by default) are retained. The `language_score` is classification confidence, not a proportion of Guarani words.
- **Consistent `.jsonl` format:** ensures all documents are saved in a standardized structure.  
- **Aggregated dataset statistics:** reports counts and average classification confidence for retained documents.

See [data formats and filtering](../../docs/data-format.md) for complete field
definitions, synthetic examples, timestamp conventions, and known limitations.

All processed outputs are stored in:

```
data/processed/
```

------------------------------------------------------------------------

## ⚙️ Script Used

The normalization and reporting are performed using:

```
src/processor/formart_data.py
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

Use Python 3.12.7 and an activated virtual environment. From the repository root,
install the processor and pinned identifier dependencies and prepare its models:

```bash
python -m pip install -c constraints/python312.txt -r requirements-build.txt
python -m pip install --no-build-isolation -c constraints/python312.txt -r src/processor/requirements.txt -r requirements-identifier.txt
python scripts/setup_identifier.py
python3 -m src.processor.formart_data
```

Choose a threshold with `--min-language-score` (inclusive, from `0` to `1`):

```bash
python -m src.processor.formart_data --min-language-score 0.85
```

The default is `0.70`. A value of `0` removes the numeric confidence cutoff but
still requires the document's predicted language to be `grn`.

Scraper dependencies are not needed for processor-only use. This script uses
`spacy.blank("xx")` for tokenization, so no downloaded spaCy language model is
required. All three identifier models are pinned and prepared by the setup
script before processing. See [reproducible setup](../../docs/setup.md) for
checkout revisions, version constraints, and troubleshooting. The processor's
requirements declare direct dependencies and the Click compatibility package;
transitive versions are pinned separately in `constraints/python312.txt`.

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
