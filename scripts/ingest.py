"""Load chunks into Azure AI Search: create the index, embed, upload, clean up.

Usage (after fetch_docs + chunk_corpus, with AZURE_* values in .env):
    python -m scripts.ingest                 # sync corpus/chunks.jsonl into the index
    python -m scripts.ingest --dry-run       # show what would change, call nothing that costs

Idempotent: only new or changed chunks (by content hash) are embedded, and
chunks that no longer exist (e.g. a repo went private) are deleted from the index.
"""
import argparse
import os
import sys

from app.azure_search import (
    build_index, chunk_to_document, doc_key, index_client_from_env, plan_sync, search_client_from_env,
)
from app.embeddings import AzureOpenAIEmbedder
from app.retrieval import load_chunks

UPLOAD_BATCH = 100


def load_env():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def existing_hashes(search_client):
    """{doc_id: content_hash} for everything currently in the index ({} if the index doesn't exist yet)."""
    try:
        from azure.core.exceptions import ResourceNotFoundError
    except ImportError:                                   # pragma: no cover
        ResourceNotFoundError = LookupError
    try:
        results = search_client.search(search_text="*", select=["id", "content_hash"], top=1000)
        return {r["id"]: r.get("content_hash") for r in results}
    except ResourceNotFoundError:
        return {}


def check_upload(results):
    failed = [r for r in results if not getattr(r, "succeeded", True)]
    if failed:
        raise RuntimeError(f"{len(failed)} document(s) failed to upload, e.g. {failed[0].key}: {failed[0].error_message}")


def sync(chunks, search_client, embedder, dry_run=False, log=print):
    """Bring the index in line with `chunks`. Returns a summary dict."""
    existing = existing_hashes(search_client)
    to_embed, unchanged, to_delete = plan_sync(chunks, existing)
    log(f"Index has {len(existing)} docs · corpus has {len(chunks)} chunks")
    log(f"  embed + upload: {len(to_embed)} · unchanged: {len(unchanged)} · delete: {len(to_delete)}")
    if dry_run:
        return {"embedded": 0, "unchanged": len(unchanged), "deleted": 0, "planned_embed": len(to_embed), "planned_delete": len(to_delete)}

    if to_embed:
        vectors = embedder.embed([c["text"] for c in to_embed])
        docs = [chunk_to_document(c, v) for c, v in zip(to_embed, vectors)]
        for start in range(0, len(docs), UPLOAD_BATCH):
            check_upload(search_client.merge_or_upload_documents(documents=docs[start:start + UPLOAD_BATCH]))
    if to_delete:
        check_upload(search_client.delete_documents(documents=[{"id": key} for key in to_delete]))
    return {"embedded": len(to_embed), "unchanged": len(unchanged), "deleted": len(to_delete)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sync chunks into Azure AI Search")
    parser.add_argument("--chunks", default="corpus/chunks.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    load_env()
    missing = [n for n in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_EMBED_DEPLOYMENT",
                           "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_API_KEY") if not os.getenv(n)]
    if missing:
        sys.exit(f"Missing in .env: {', '.join(missing)} (run python -m scripts.check_azure)")

    index_name = os.getenv("AZURE_SEARCH_INDEX", "ask-barry-chunks")
    chunks = load_chunks(args.chunks)
    ids = [doc_key(c["chunk_id"]) for c in chunks]
    if len(ids) != len(set(ids)):
        sys.exit("Duplicate chunk_ids in chunks.jsonl; re-run python -m scripts.chunk_corpus")

    if not args.dry_run:
        index_client_from_env().create_or_update_index(build_index(index_name))
        print(f"Index '{index_name}' ready")
    embedder = AzureOpenAIEmbedder()
    summary = sync(chunks, search_client_from_env(index_name), embedder, dry_run=args.dry_run)
    print(f"Done: {summary} · embedding API calls: {embedder.calls}")


if __name__ == "__main__":
    main()
