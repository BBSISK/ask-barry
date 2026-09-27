"""Chunk every document listed in corpus/manifest.json.

Usage (after python -m scripts.fetch_docs):
    python -m scripts.chunk_corpus               # writes corpus/chunks.jsonl
    python -m scripts.chunk_corpus --max-chars 1500

Prints a per-repo summary so you can sanity-check what will be searchable.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from app.chunking import DEFAULT_MAX_CHARS, chunk_markdown


def chunk_corpus(corpus_dir, max_chars=DEFAULT_MAX_CHARS):
    corpus_dir = Path(corpus_dir)
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    chunks = []
    for doc in manifest["documents"]:
        text = (corpus_dir / doc["local_path"]).read_text(encoding="utf-8")
        chunks.extend(chunk_markdown(
            text, repo=doc["repo"], path=doc["path"], url=doc["url"],
            commit_sha=doc["commit_sha"], max_chars=max_chars,
        ))
    return chunks


def main(argv=None):
    parser = argparse.ArgumentParser(description="Chunk the fetched corpus")
    parser.add_argument("--corpus", default="corpus")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args(argv)

    chunks = chunk_corpus(args.corpus, args.max_chars)
    out = Path(args.corpus) / "chunks.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict()) + "\n")

    per_repo = Counter(c.repo for c in chunks)
    sizes = [len(c.text) for c in chunks] or [0]
    print(f"{len(chunks)} chunks from {len(per_repo)} repos -> {out}")
    for repo, n in per_repo.most_common():
        print(f"  {repo:<28} {n:>4}")
    print(f"chunk size (chars): min {min(sizes)}, avg {sum(sizes) // len(sizes)}, max {max(sizes)}")


if __name__ == "__main__":
    main()
