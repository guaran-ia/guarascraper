import os
import json
import spacy
from tqdm import tqdm
from pathlib import Path
from urllib.parse import urlparse
import sys
import argparse
import math

# The language identifier repository is cloned to <repository root>/corpus.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIN_LANGUAGE_SCORE = 0.70
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.language_identifier import create_identifier


# ============================
# UTILITY FUNCTIONS
# ============================

def word_count_split(text: str) -> int:
    """Count words using simple whitespace split."""
    return len(text.split())


def word_count_spacy(text: str, tokenizer, include_punct: bool = False) -> int:
    """Count words using spaCy tokenizer."""
    tokens = []
    for token in tokenizer(text):
        if not include_punct and token.is_punct:
            continue
        tokens.append(token.text)
    return len(tokens)


def write_jsonl_line(file, obj: dict) -> None:
    """Write a single JSONL line to file."""
    file.write(json.dumps(obj, ensure_ascii=False) + "\n")


def extract_domain(url: str) -> str:
    """Extract domain name from URL."""
    if not url:
        return ""
    domain = urlparse(url).netloc.lower()
    return domain[4:] if domain.startswith("www.") else domain


def get_empty_report() -> dict:
    """Initialize an empty aggregated report."""
    return {
        "num_docs": 0,
        "num_words_split": 0,
        "num_words_punct_spacy": 0,
        "num_words_no_punct_spacy": 0,
        "num_chars": 0,
        "sum_lang_score": 0,
        "avg_words_split": 0,
        "avg_words_punct_spacy": 0,
        "avg_words_no_punct_spacy": 0,
        "avg_chars": 0,
        "avg_language_score": 0,
    }



def finalize_report(report: dict) -> dict:
    """Compute average values for the aggregate report."""

    n = report["num_docs"]
    if n > 0:
        # Compute averages for words and characters
        report["avg_words_split"] = report["num_words_split"] / n
        report["avg_words_punct_spacy"] = report["num_words_punct_spacy"] / n
        report["avg_words_no_punct_spacy"] = report["num_words_no_punct_spacy"] / n
        report["avg_chars"] = report["num_chars"] / n
        report["avg_language_score"] = report["sum_lang_score"] / n

    return report

def identify_language(text: str, identifier, gn_code: str,
                      min_language_score: float = MIN_LANGUAGE_SCORE) -> dict | None:
    """
    Identify language for a given text and return language information
    only if the predicted language is Guarani and meets the confidence threshold.
    """
    clean_text = " ".join(text.split())
    if not clean_text.strip():
        return None

    result = identifier.identify_languages(clean_text, k=1, raw_output=False)
    lang = result["languages"]

    if lang[0] == gn_code and lang[1] >= min_language_score:
        return {
            "lang": lang[0],
            "score": lang[1],
            "source_score": result["source"],
            "voting_method": result["voting"],
        }

    return None


# ============================
# MAIN PROCESS
# ============================

def confidence_threshold(value: str) -> float:
    score = float(value)
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise argparse.ArgumentTypeError("must be a finite number between 0 and 1")
    return score


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Normalize and filter downloaded Guarani documents.")
    parser.add_argument(
        "--min-language-score", type=confidence_threshold, default=MIN_LANGUAGE_SCORE,
        help="Minimum Guarani classification confidence to retain a document (0–1; default: 0.70)",
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)

    # ANSI colors
    BLUE = "\033[34m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    GN_CODE = "grn"

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    INPUT_DIR = BASE_DIR / "data" / "download"
    OUTPUT_DIR = BASE_DIR / "data" / "processed"

    FINAL_JSONL = OUTPUT_DIR / "all_domains.jsonl"
    FINAL_REPORT = OUTPUT_DIR / "all_domains_report.json"

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tokenizer = spacy.blank("xx")
    identifier = create_identifier()

    print(f"{BLUE}=== Processing all domains ==={RESET}")
    print(f"Minimum Guarani classification confidence: {args.min_language_score:g}")

    files = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith(".jsonl")])
    num_domains = len(files)

    file_line_counts = {}
    total_docs = 0

    for filename in files:
        path = INPUT_DIR / filename
        with open(path, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f)
        file_line_counts[filename] = count
        total_docs += count

    if total_docs == 0:
        print("No documents found to process.")
        return

    report = get_empty_report()

    with open(FINAL_JSONL, "w", encoding="utf-8") as outfile, \
         tqdm(total=total_docs, desc="Global progress", ncols=100) as bar:

        for domain_index, filename in enumerate(files, start=1):
            input_path = INPUT_DIR / filename
            domain_total = file_line_counts[filename]

            with open(input_path, "r", encoding="utf-8") as infile:
                for doc_index, line in enumerate(infile, start=1):

                    postfix_msg = (
                        f"{GREEN}Domain {domain_index}/{num_domains}{RESET} | "
                        f"{YELLOW}Doc {doc_index}/{domain_total}{RESET} | "
                        f"{filename}"
                    )
                    bar.set_postfix_str(postfix_msg)
                    bar.update(1)

                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    text = obj.get("text", "")
                    clean_text = " ".join(text.split())

                    if not clean_text:
                        continue

                    num_words_split = word_count_split(clean_text)
                    num_words_punct = word_count_spacy(clean_text, tokenizer, include_punct=True)
                    num_words_no_punct = word_count_spacy(clean_text, tokenizer, include_punct=False)
                    num_chars = len(clean_text)

                    lang_info = identify_language(clean_text, identifier, GN_CODE, args.min_language_score)

                    if lang_info:
                        lang = lang_info["lang"]
                        lang_score = lang_info["score"]
                        lang_src = lang_info["source_score"]
                        lang_method = lang_info["voting_method"]
                    else:
                        continue

                    new_doc = {
                        "text": clean_text,
                        "corpus": obj.get("corpus", ""),
                        "corpus_file": obj.get("corpus_file", ""),
                        "source": extract_domain(obj.get("url", "")),
                        "url": obj.get("url", ""),
                        "language": lang,
                        "language_score": lang_score,
                        "language_script": "Latn",
                        "language_score_source": lang_src,
                        "language_identification_method": lang_method,
                        "num_words_split": num_words_split,
                        "num_words_punct_spacy": num_words_punct,
                        "num_words_no_punct_spacy": num_words_no_punct,
                        "num_chars": num_chars                    
                    }
                    write_jsonl_line(outfile, new_doc)
                    report["num_docs"] += 1
                    report["num_words_split"] += num_words_split
                    report["num_words_punct_spacy"] += num_words_punct
                    report["num_words_no_punct_spacy"] += num_words_no_punct
                    report["num_chars"] += num_chars
                    report["sum_lang_score"] += lang_score
    report = finalize_report(report)

    with open(FINAL_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"\n{GREEN}✔ Combined corpus created:{RESET} {FINAL_JSONL}")
    print(f"{GREEN}✔ Global report generated:{RESET} {FINAL_REPORT}")
    print(f"{BLUE}=== COMPLETED ✔ ==={RESET}")


if __name__ == "__main__":
    main()
