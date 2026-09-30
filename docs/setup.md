# Reproducible setup and troubleshooting

## What is pinned

* CPython **3.12.7** is the locally tested interpreter.
* `identifier.lock.json` pins the external `corpus` commit, each of the three
  model repository commits, and each model's SHA-256 digest.
* `requirements*.txt` and `src/processor/requirements.txt` declare component
  dependencies; `constraints/python312.txt` pins their resolved transitive
  versions and the build tools used for FastText.

Install both component requirements and constraints. Installing only a
requirements file permits pip to choose newer transitive versions and does not
reproduce the tested environment. Constraints do not install packages by
themselves. They pin versions, not platform-specific wheel hashes or the C++
compiler; builds across operating systems are not promised to be bit-identical.
The optional legacy detector is outside this constrained active runtime.

## Full clean-clone setup

On Linux, a FastText source build needs a C++ compiler and matching Python
development headers (commonly supplied by `build-essential` and `python3-dev`
on Debian/Ubuntu). On macOS, install Xcode Command Line Tools when a compiler
is unavailable. Allow about 4.1 GB for models plus package/cache space; downloading
and loading all models takes longer than running the offline unit tests.

```bash
git clone https://github.com/guaran-ia/guarascraper.git
cd guarascraper
python3.12 -m venv venv
source venv/bin/activate
python -m pip install -c constraints/python312.txt -r requirements-build.txt
python -m pip install --no-build-isolation -c constraints/python312.txt -r requirements-runtime.txt
python -m pip check
python scripts/setup_identifier.py
python scripts/integration_check.py
```

Ensure `python3.12 --version` reports `3.12.7` when reproducing the exact tested
interpreter. Installations and model setup require network access. Once models
are prepared, classification uses cached pinned files; it does not auto-update
or download models on first use.

The bootstrap creates a sparse detached checkout of
`d599a2e4ae065f8708c7b15aefc30c0832760d33` containing the identifier source and
its ISO-code mapping. It refuses unexpected or locally modified source rather
than altering an existing checkout. The adapter inherits upstream prediction
and voting logic and overrides model loaders to select the exact cached
artifacts. GlotLID, Facebook FastText, and OpenLID are all enabled; missing
models fail setup/runtime rather than silently reducing the voting ensemble.

### Third-party code and model terms

The pinned `corpus` checkout is GPL-3.0 licensed. Model terms are independent of
the repository's Apache-2.0 code license and remain subject to the upstream
artifacts' notices:

| Artifact | Upstream terms indicated by model/source metadata |
| --- | --- |
| Identifier source | [Guaran-IA corpus](https://github.com/guaran-ia/corpus), GPL-3.0 |
| GlotLID model | [cis-lmu/glotlid](https://huggingface.co/cis-lmu/glotlid), Apache-2.0 with notices; review its pinned `LICENSE` |
| FastText model | [Facebook language-identification model](https://huggingface.co/facebook/fasttext-language-identification), CC-BY-NC-4.0 |
| OpenLID model | [laurievb/OpenLID](https://huggingface.co/laurievb/OpenLID), GPL-3.0 per the pinned model card |

Setup downloads the model files into the external checkout; it does not commit
or redistribute them. Check the upstream terms for your intended use, especially
the non-commercial term on the Facebook FastText model.

## Component-only environments

After creating a virtual environment and installing `requirements-build.txt`
with the constraints, install only the needed components:

```bash
# Scraper plus real identifier
python -m pip install --no-build-isolation -c constraints/python312.txt -r requirements.txt -r requirements-identifier.txt

# Processor plus real identifier
python -m pip install --no-build-isolation -c constraints/python312.txt -r src/processor/requirements.txt -r requirements-identifier.txt
```

Run `python scripts/setup_identifier.py` in either case. Offline scraper checks
need only `requirements-ci.txt`, with the constraints; processor unit tests
need only the processor requirements, with the constraints. Neither unit-test
suite needs model downloads.

## Integration check

`python scripts/integration_check.py` serves
`tests/fixtures/integration/index.html` and its robots.txt on localhost. It:

1. Copies the current source and identifier manifest into a fresh temporary
   workspace, excluding local caches and model binaries.
2. Runs the actual domain-crawl CLI through Scrapy's HTTP downloader and all
   three real model backends, including starting-page extraction.
3. Checks that Guarani text is retained while the English control and script
   content are excluded, with the expected identity and source URL.
4. Runs the actual processor CLI at the default 0.70 confidence threshold and
   validates a retained document, counts, and aggregate report.
5. Repeats the crawl, checking unchanged raw output and no second page fetch.

Only fixtures are fetched, and all output is temporary. This validates runtime
integration, not general model accuracy or production website behavior. It
has passed locally on Python 3.12.7/macOS arm64; the manual **Real-model
integration** GitHub Actions workflow runs the same check on Ubuntu. The
ordinary CI workflow remains lightweight and uses mocked model inference.

## Troubleshooting

### Missing or unexpected identifier checkout

Run `python scripts/setup_identifier.py`. A non-Git directory named `corpus/`
may already hold other local data; preserve it and select a different location:

```bash
export GUARASCRAPER_CORPUS_DIR="$HOME/guarascraper-identifier"
python scripts/setup_identifier.py
```

Keep that environment variable set for both the CLI and processor. Passing
`--corpus-dir` to the setup script selects a setup location only; runtime also
needs `GUARASCRAPER_CORPUS_DIR` when the location is not `<project>/corpus`.
An existing wrong-revision or modified checkout is rejected. Use a fresh
location instead of discarding changes in an unrelated checkout.

### Missing models, interrupted download, or checksum mismatch

Rerun `python scripts/setup_identifier.py`. Hugging Face manages partial
downloads and reuses completed cached artifacts. The script checks all three
hashes, including already cached models. Check disk space and connectivity to
Hugging Face. If the Xet download transport fails, try:

```bash
HF_HUB_DISABLE_XET=1 python scripts/setup_identifier.py
```

For a checksum mismatch, remove only the affected cached artifact reported by
Hugging Face and rerun setup to download it again. Do not edit the expected
hash to make an unverified file pass. Model loading requires enough available
memory for all three backends; a killed process may indicate insufficient RAM.

### FastText or native-package build failures

Use Python 3.12.7, a matching C++ toolchain, and the pinned build-tool installation
before installing runtime requirements with `--no-build-isolation`. Errors
mentioning `pybind11`, a missing compiler, or `Python.h` usually indicate missing
build tools or Python headers. A fresh virtual environment helps avoid mixing
older NumPy/spaCy binary extensions with the constrained versions.

### Scrapy HTTP-handler import errors

Install with the constraints. The integration run found that newer Twisted
releases removed a private API used by Scrapy 2.13; the tested constraints pin
a compatible networking stack. `pip check` alone does not detect every runtime
API incompatibility. Run the integration check after dependency updates.

### Empty raw or processed output

* Inspect console output and `logs/scraper_errors.log` for downloader, model,
  or identifier errors; Scrapy may finish without producing records after a
  download failure.
* Check whether the URL is excluded by FineWeb2 or existing downloaded records,
  robots.txt, crawl limits, or a disabled redirect. Known starting pages are
  skipped and cannot supply links to unknown pages.
* Raw output requires at least one body-text chunk with four words and a `grn`
  prediction. JavaScript-rendered content, short chunks, and other languages
  may yield no records.
* Processing requires JSONL files under `data/download/` containing nonempty
  text classified as `grn` with confidence at least `--min-language-score`
  (default 0.70). A model score is not a word-language percentage.
* If the processor has no input lines, it produces no new output. If input
  lines exist but all are rejected, the combined output is empty and the report
  has zero retained documents. See [data formats](data-format.md).

## Updating pins

Use a fresh Python 3.12.7 environment when intentionally updating dependencies.
Update direct requirements as needed, resolve the runtime, run both unit-test
suites and `scripts/integration_check.py`, and use `python -m pip freeze --all`
to capture the tested resolved versions in the separate constraints file.
When updating the external identifier or models, update their exact revisions
and verified digests in `identifier.lock.json` and repeat the real-model check.
Commit source/pin changes together; keep downloaded binaries and local outputs
outside version control. GitHub's model-cache key follows the manifest hash.
