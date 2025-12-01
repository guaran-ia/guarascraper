import os
import json
import spacy
from tqdm import tqdm
from pathlib import Path

from urllib.parse import urlparse
from src.corpus.src.pipeline.language_identifier.language_identifier import LanguageIdentifier


# ============================
# COLORES ANSI
# ============================
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# ============================
# CONFIGURACIÓN
# ============================


BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = BASE_DIR / "data" / "download"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

FINAL_JSONL = os.path.join(OUTPUT_DIR, "all_domains.jsonl")
FINAL_REPORT = os.path.join(OUTPUT_DIR, "all_domains_report.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# tokenizer
word_seg = spacy.blank("xx")

# identificador de lenguaje
identifier = LanguageIdentifier(glotlid=True, fasttext=True, openlid=True)
GN_CODE = 'grn'


# ============================
# FUNCIONES ORIGINALES
# ============================

def word_count_split(text):
    return len(text.split())


def word_count_spacy(text, include_punct=False):
    tokens = []
    for t in word_seg(text):
        if not include_punct and t.is_punct:
            continue
        tokens.append(t.text)
    return len(tokens)


def identify_language(text):
    clean_text = " ".join(text.split())
    if not clean_text.strip():
        return None

    result = identifier.identify_languages(clean_text, k=1, raw_output=False)
    lang = result["languages"]

    if lang[0] == GN_CODE:
        return {
            "lang": lang[0],
            "score": lang[1],
            "source_score": result["source"],
            "voting_method": result["voting"],
        }
    return None


def write_jsonl_line(file, obj):
    file.write(json.dumps(obj, ensure_ascii=False) + "\n")


def extract_domain(url):
    if not url:
        return ""
    domain = urlparse(url).netloc.lower()
    return domain[4:] if domain.startswith("www.") else domain


def get_empty_report():
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
        "avg_language_score": 0
    }


def finalize_report(report):
    n = report["num_docs"]
    if n > 0:
        report["avg_words_split"] = report["num_words_split"] / n
        report["avg_words_punct_spacy"] = report["num_words_punct_spacy"] / n
        report["avg_words_no_punct_spacy"] = report["num_words_no_punct_spacy"] / n
        report["avg_chars"] = report["num_chars"] / n
        report["avg_language_score"] = report["sum_lang_score"] / n
    return report


# ============================
# PROCESO PRINCIPAL
# ============================

def main():
    print(f"{BLUE}=== Procesando TODOS los dominios ==={RESET}")

    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".jsonl")]
    files.sort()
    num_domains = len(files)

    # contar documentos totales
    file_line_counts = {}
    total_docs = 0

    for fn in files:
        path = os.path.join(INPUT_DIR, fn)
        with open(path, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f)
        file_line_counts[fn] = count
        total_docs += count

    if total_docs == 0:
        print("No hay documentos para procesar.")
        return

    report = get_empty_report()

    # === UNA SOLA BARRA GLOBAL ===
    with open(FINAL_JSONL, "w", encoding="utf-8") as outfile, \
         tqdm(total=total_docs, desc=f"{BLUE}Progreso global{RESET}", ncols=100) as bar:

        global_index = 0

        for domain_index, filename in enumerate(files, start=1):
            input_path = os.path.join(INPUT_DIR, filename)
            domain_total = file_line_counts[filename]

            with open(input_path, "r", encoding="utf-8") as infile:

                for doc_index, line in enumerate(infile, start=1):
                    global_index += 1

                    # colores en postfix
                    postfix_msg = (
                        f"{GREEN}Dom {domain_index}/{num_domains}{RESET} | "
                        f"{YELLOW}Doc {doc_index}/{domain_total}{RESET} | "
                        f"{filename}"
                    )
                    bar.set_postfix_str(postfix_msg)

                    bar.update(1)

                    # =====================
                    # PROCESAMIENTO REAL
                    # =====================

                    try:
                        obj = json.loads(line)
                    except:
                        continue

                    text = obj.get("text", "")
                    clean_text = " ".join(text.split())

                    num_words_split = word_count_split(clean_text)
                    num_words_punct = word_count_spacy(clean_text, include_punct=True)
                    num_words_no_punct = word_count_spacy(clean_text, include_punct=False)
                    num_chars = len(clean_text)

                    lang_info = identify_language(clean_text)
                    if lang_info:
                        lang = lang_info["lang"]
                        lang_score = lang_info["score"]
                        lang_src = lang_info["source_score"]
                        lang_method = lang_info["voting_method"]
                    else:
                        lang = ""
                        lang_score = 0.0
                        lang_src = ""
                        lang_method = ""

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

                    # actualizar reporte
                    report["num_docs"] += 1
                    report["num_words_split"] += num_words_split
                    report["num_words_punct_spacy"] += num_words_punct
                    report["num_words_no_punct_spacy"] += num_words_no_punct
                    report["num_chars"] += num_chars
                    report["sum_lang_score"] += lang_score

    report = finalize_report(report)

    with open(FINAL_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"\n{GREEN}✔ Corpus combinado:{RESET} {FINAL_JSONL}")
    print(f"{GREEN}✔ Reporte global:{RESET} {FINAL_REPORT}")
    print(f"{BLUE}=== COMPLETADO ✔ ==={RESET}")


if __name__ == "__main__":
    main()
