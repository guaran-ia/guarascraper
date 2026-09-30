"""Fetch the exact identifier checkout and verify downloaded model artifacts."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.language_identifier import corpus_directory, identifier_config, verify_checkout


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, default=corpus_directory())
    parser.add_argument("--skip-models", action="store_true", help="Fetch source only; no model dependencies needed")
    args = parser.parse_args()
    config = identifier_config()
    directory = args.corpus_dir.resolve()
    if not directory.exists():
        directory.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", config["repository"], str(directory)], check=True)
        subprocess.run(["git", "-C", str(directory), "sparse-checkout", "init", "--cone"], check=True)
        subprocess.run(["git", "-C", str(directory), "sparse-checkout", "set", config["source_directory"]], check=True)
        subprocess.run(["git", "-C", str(directory), "checkout", "--detach", config["revision"]], check=True)
    verify_checkout(directory, config)
    print(f"Identifier revision: {config['revision']}", flush=True)
    if args.skip_models:
        return

    from huggingface_hub import hf_hub_download

    cache = directory / config["source_directory"] / "models"
    cache.mkdir(parents=True, exist_ok=True)
    for name, model in config["models"].items():
        print(f"Preparing {name}...", flush=True)
        path = Path(hf_hub_download(
            repo_id=model["repo_id"], revision=model["revision"],
            filename=model["filename"], cache_dir=cache,
        ))
        digest = sha256(path)
        if digest != model["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch for {name} at {path}: {digest}; expected {model['sha256']}")
        print(f"{name} sha256: {digest}", flush=True)


if __name__ == "__main__":
    main()
