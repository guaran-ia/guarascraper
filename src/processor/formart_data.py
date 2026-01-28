import os
import json
import spacy
from tqdm import tqdm
from pathlib import Path
from urllib.parse import urlparse
import re
from src.corpus.src.pipeline.language_identifier.language_identifier import LanguageIdentifier


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
    """Compute average values for the aggregated report and update README automatically."""

    n = report["num_docs"]
    if n > 0:
        # Compute averages for words and characters
        report["avg_words_split"] = report["num_words_split"] / n
        report["avg_words_punct_spacy"] = report["num_words_punct_spacy"] / n
        report["avg_words_no_punct_spacy"] = report["num_words_no_punct_spacy"] / n
        report["avg_chars"] = report["num_chars"] / n
        report["avg_language_score"] = report["sum_lang_score"] / n

    # ---------------------------
    # AUTOMATIC README UPDATE
    # ---------------------------

    README_FILE = Path(__file__).resolve().parent / "README.md"

    if README_FILE.exists():
        with open(README_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Safe replacements using lambda functions
        replacements = [
            (r"(\*\*Total number of documents:\*\*\s*)[\d,]+", f"{report['num_docs']:,}"),
            (r"(\*\*Average language score:\*\*\s*)[0-9.]+", f"{report['avg_language_score']:.6f}"),
            (r"(\*\*Average number of words using `split\(\)`:\*\*\s*)[0-9.]+", f"{report['avg_words_split']:.2f}"),
            (r"(\*\*Average number of words using `spacy` with punctuation:\*\*\s*)[0-9.]+", f"{report['avg_words_punct_spacy']:.2f}"),
            (r"(\*\*Average number of words using `spacy` without punctuation:\*\*\s*)[0-9.]+", f"{report['avg_words_no_punct_spacy']:.2f}"),
            (r"(\*\*Total number of words using `split\(\)`:\*\*\s*)[\d,]+", f"{report['num_words_split']:,}"),
            (r"(\*\*Total number of words using `spacy` with punctuation:\*\*\s*)[\d,]+", f"{report['num_words_punct_spacy']:,}"),
            (r"(\*\*Total number of words using `spacy` without punctuation:\*\*\s*)[\d,]+", f"{report['num_words_no_punct_spacy']:,}"),
            (r"(\*\*Average number of characters:\*\*\s*)[0-9.]+", f"{report['avg_chars']:.2f}"),
            (r"(\*\*Total number of characters:\*\*\s*)[\d,]+", f"{report['num_chars']:,}"),
        ]

        for pattern, value in replacements:
            content = re.sub(pattern, lambda m: m.group(1) + value, content)

        # Save updated README
        with open(README_FILE, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ README updated at {README_FILE}")
    else:
        print(f"⚠️ README not found at {README_FILE}, skipping update.")


    return report

def identify_language(text: str, identifier, gn_code: str) -> dict | None:
    """
    Identify language for a given text and return language information
    only if the predicted language is Guarani.
    """
    clean_text = " ".join(text.split())
    if not clean_text.strip():
        return None

    result = identifier.identify_languages(clean_text, k=1, raw_output=False)
    lang = result["languages"]

    if lang[0] == gn_code:
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

def main() -> None:
    # ANSI colors
    BLUE = "\033[34m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"
    MIN_LANGUAGE_SCORE = 0.70

    GN_CODE = "grn"

    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    INPUT_DIR = BASE_DIR / "data" / "download"
    OUTPUT_DIR = BASE_DIR / "data" / "processed"

    FINAL_JSONL = OUTPUT_DIR / "all_domains.jsonl"
    FINAL_REPORT = OUTPUT_DIR / "all_domains_report.json"

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tokenizer = spacy.blank("xx")
    identifier = LanguageIdentifier(glotlid=True, fasttext=True, openlid=True)

    print(f"{BLUE}=== Processing all domains ==={RESET}")

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

                    lang_info = identify_language(clean_text, identifier, GN_CODE)

                    if lang_info  and lang_info['lang'] == GN_CODE:
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