# Data formats and filtering

This document describes the output of the current scraper and processor.
Examples use invented Guarani text and reserved `example.org` URLs, not scraped
material. Language scores and model metadata are illustrative; they are not
results of running the models on these examples.

## Files and encoding

| Output | Location | Format |
| --- | --- | --- |
| Raw accepted page content | `data/download/<domain>.jsonl` | UTF-8 JSON Lines |
| Processed accepted documents | `data/processed/all_domains.jsonl` | UTF-8 JSON Lines |
| Aggregate report | `data/processed/all_domains_report.json` | UTF-8 JSON object |

JSONL files have one complete JSON object per physical line. Embedded newlines
are escaped as `\n` within the JSON string. Unicode characters are written
directly rather than escaped. Objects below are pretty-printed for readability;
the actual JSONL records are each written on a single line.

Domain filenames use the lowercase hostname with only an exact `www.` prefix
removed. Other subdomains remain in the filename.

## Raw page record

```json
{
  "text": "Ñande ñe’ẽ iporã ha oikove.\nÑañe’ẽ guaraníme ñande róga ha mbo’ehaópe.",
  "date": "2026-09-30T14:22:18.123456",
  "url": "https://www.example.org/gn/ñe’ẽ"
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `text` | string | Accepted text chunks for the page, concatenated with newline separators. This is not necessarily the complete page text. |
| `date` | string | UTC timestamp when this record was written or most recently merged with another chunk in the current run. |
| `url` | string | Source response URL. When chunks are merged, the existing record's URL is retained. |

The scraper's internal item has `word`, `url`, and `domain` fields. Despite the
name `word`, it carries a text chunk, not a single word. The pipeline writes
only `text`, `date`, and `url`; model scores are not stored in raw records.

### Timestamp conventions

The current writer uses `datetime.utcnow().isoformat()`. Raw `date` values are
UTC **by convention**, but contain neither a `Z` suffix nor a timezone offset.
Consumers should interpret them as UTC rather than as local time. They are
collection/write timestamps, not source publication dates or HTTP modification
times. Merging a new chunk updates the timestamp; skipping an existing record
leaves it unchanged.

The processor currently does **not** retain `date` in its output. Keep the raw
files when collection-time provenance is needed; the processed format alone
cannot reconstruct it.

## Processed document record

The processor normalizes the raw example to one space-separated string and
classifies the combined text again:

```json
{
  "text": "Ñande ñe’ẽ iporã ha oikove. Ñañe’ẽ guaraníme ñande róga ha mbo’ehaópe.",
  "corpus": "",
  "corpus_file": "",
  "source": "example.org",
  "url": "https://www.example.org/gn/ñe’ẽ",
  "language": "grn",
  "language_score": 0.92,
  "language_script": "Latn",
  "language_score_source": "glotlid",
  "language_identification_method": "agree_glotlib_fasttext_openlid",
  "num_words_split": 11,
  "num_words_punct_spacy": 13,
  "num_words_no_punct_spacy": 11,
  "num_chars": 70
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `text` | string | Raw text after `" ".join(text.split())`: leading/trailing whitespace removed and whitespace runs replaced with a single space. |
| `corpus` | string, normally | Copied from input if present; otherwise `""`. The scraper does not populate it. |
| `corpus_file` | string, normally | Copied from input if present; otherwise `""`. It is not automatically set to the input filename. |
| `source` | string | Lowercase URL network location with an exact `www.` prefix removed; a port, if present, is retained. Empty when the URL is absent. |
| `url` | string | Copied from input; defaults to `""` when absent. |
| `language` | string | Identifier prediction, required to be `grn` (Guarani) for retention. |
| `language_score` | number | Confidence score returned by the external language identifier, required to meet `--min-language-score` (`0.70` by default). It is not the proportion of Guarani words or an independently calibrated probability. |
| `language_script` | string | Fixed value `Latn`; this is not a separately detected script. |
| `language_score_source` | string, normally | Identifier's `source` value, copied without transformation. Exact values depend on the external identifier revision. |
| `language_identification_method` | string, normally | Identifier's `voting` value, copied without transformation. Exact values depend on the external identifier revision. |
| `num_words_split` | integer | Number of whitespace-separated tokens in normalized text, using `len(text.split())`. |
| `num_words_punct_spacy` | integer | Number of tokens from `spacy.blank("xx")`, including punctuation tokens. |
| `num_words_no_punct_spacy` | integer | Number of spaCy tokens excluding those with `is_punct=True`. |
| `num_chars` | integer | Python `len(text)` of normalized text: Unicode code points including spaces and punctuation, not bytes or grapheme clusters. |

Input metadata is copied without type validation, so these descriptive types
are not a schema-validation guarantee. Counts can differ between tokenizers;
neither word-count method is a Guarani morphological analysis. The example's
counts were checked with spaCy 3.8.11's blank multilingual tokenizer.

## Filtering rules

### Scraper

1. Exclude URLs found in the domain-specific FineWeb2 CSV, the shared FineWeb2
   CSV, or previous downloaded JSONL output. See the
   [collection-state behavior](../README.md#previously-collected-pages-and-fineweb2-exclusions).
2. Select body text nodes while excluding script, style, noscript, SVG, and
   iframe descendants. This is DOM text extraction, not rendered-page analysis.
3. Replace newline and carriage-return characters within each chunk with
   spaces, then strip its ends.
4. Discard empty chunks and chunks with fewer than four whitespace-separated
   words.
5. Call the external identifier with `k=1`, with GlotLID, FastText, and OpenLID
   enabled. Retain chunks whose returned language is `grn`. The scraper itself
   adds **no numeric confidence threshold**.
6. Merge accepted chunks for a new page into a raw page record. A page with no
   accepted chunks produces no record.

### Processor

1. Read each `.jsonl` file directly under `data/download/` in sorted filename
   order, preserving input record order within each file.
2. Skip invalid JSON lines. Missing `text` defaults to `""`; normalize whitespace
   and skip empty text.
3. Reclassify the combined normalized document with the same external
   identifier configuration.
4. Retain it only when the returned language is `grn` **and confidence meets
   the selected threshold**. The default is `0.70`, inclusive: exactly `0.70`
   passes with the default threshold; lower scores do not.
5. Write the retained record and include it in aggregate statistics.

Set the processor threshold with, for example:

```bash
python -m src.processor.formart_data --min-language-score 0.85
```

Values must be finite numbers between `0` and `1`. `MIN_LANGUAGE_SCORE` in
`src/processor/formart_data.py` defines the default of `0.70`; `0` removes the
numeric cutoff while retaining the Guarani-language check. The selected value
is printed at startup. It applies to document-level classification,
not to each word or the scraper's individual chunks. Earlier versions declared
this threshold but did not apply it; rerunning processing can therefore reduce
the document count compared with older outputs. Classification as `grn` is
still required even when another language has a high confidence score.

## Aggregate report

`all_domains_report.json` contains statistics for **retained processed records
only**, not every fetched page or input line:

| Field(s) | Meaning |
| --- | --- |
| `num_docs` | Count of retained documents. |
| `num_words_split`, `num_words_punct_spacy`, `num_words_no_punct_spacy`, `num_chars` | Sums of the corresponding record-level counts. |
| `sum_lang_score` | Sum of retained document confidence scores. |
| `avg_words_split`, `avg_words_punct_spacy`, `avg_words_no_punct_spacy`, `avg_chars` | Corresponding totals divided by `num_docs`. |
| `avg_language_score` | `sum_lang_score / num_docs`, weighting each document equally regardless of length. |

When input lines exist but none pass filtering, these values remain zero. If
there are no input lines, the processor returns without generating new output.
The report does not include rejection counts or reasons.

## Known limitations

* Accepted text can include navigation, boilerplate, hidden elements, or mixed
  languages. Chunk filtering can omit short but valid Guarani passages and text
  split across inline elements. JavaScript-rendered content is not captured.
* Model confidence is not a human-validated language-purity measure. Model
  versions, voting behavior, tokenizer versions, and orthographic variation can
  affect classification and counts; record dependency and model revisions for
  comparisons between runs. The reproducible setup pins the identifier and all
  three model revisions in `identifier.lock.json`, with dependency versions in
  `constraints/python312.txt`.
* Existing records prevent recollection; their contents are not automatically
  refreshed when source pages change. No-record pages can be visited again.
  There is no general exact-text or near-duplicate deduplication across URLs.
* Raw output does not retain HTML, response headers, per-chunk confidence,
  model revision, publication date, or source license. Processed output drops
  collection timestamps and input fields other than those listed above.
* Valid JSON with unexpected types (for example `text: null` or a JSON array)
  is not generally validated and may fail processing. Identifier failures may
  also interrupt a run.
* Processing overwrites the combined output and report rather than appending.
  The combined output is not written atomically; interruption can leave a
  partial dataset and a report from a previous run.
* Unicode whitespace normalization does not perform NFC/NFD normalization;
  visually identical text can have different code-point counts.
