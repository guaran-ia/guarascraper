"""Load the pinned external identifier with pinned, pre-downloaded models."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def identifier_config():
    return json.loads((ROOT / "identifier.lock.json").read_text(encoding="utf-8"))


def corpus_directory():
    return Path(os.environ.get("GUARASCRAPER_CORPUS_DIR", ROOT / "corpus")).resolve()


def verify_checkout(directory, config):
    if not (directory / ".git").exists():
        raise RuntimeError(f"Missing identifier checkout at {directory}; run scripts/setup_identifier.py")
    source = directory / config["source_directory"]
    if not (source / "language_identifier.py").is_file() or not (source / "res" / "iso6393_macro.csv").is_file():
        raise RuntimeError(f"Identifier checkout is missing required source/assets at {source}; run scripts/setup_identifier.py")
    revision = subprocess.check_output(
        ["git", "-C", str(directory), "rev-parse", "HEAD"], text=True,
    ).strip()
    if revision != config["revision"]:
        raise RuntimeError(f"Identifier revision is {revision}; expected {config['revision']}")
    changes = subprocess.check_output(
        ["git", "-C", str(directory), "status", "--porcelain", "--untracked-files=no", "--", config["source_directory"]],
        text=True,
    )
    if changes.strip():
        raise RuntimeError("Identifier source has local changes; use a clean pinned checkout")


def create_identifier():
    """Use upstream classification logic; only model loading is overridden."""
    import fasttext
    from huggingface_hub import hf_hub_download

    config = identifier_config()
    directory = corpus_directory()
    verify_checkout(directory, config)
    source = directory / config["source_directory"]
    spec = importlib.util.spec_from_file_location("guarascraper_external_identifier", source / "language_identifier.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def load_model(name):
        model = config["models"][name]
        cache = source / "models"
        try:
            path = hf_hub_download(
                repo_id=model["repo_id"], filename=model["filename"],
                revision=model["revision"], cache_dir=cache, local_files_only=True,
            )
        except Exception as error:
            raise RuntimeError(f"Missing pinned {name} model; run scripts/setup_identifier.py") from error
        return fasttext.load_model(str(path))

    class PinnedIdentifier(module.LanguageIdentifier):
        def load_glotlid_model(self, verbose=False):
            return load_model("glotlid")

        def load_fasttext_model(self, verbose=False):
            return load_model("fasttext")

        def load_openlid_model(self, verbose=False):
            return load_model("openlid")

    return PinnedIdentifier(glotlid=True, fasttext=True, openlid=True)
