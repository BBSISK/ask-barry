"""Azure AI Search: index definition, document mapping and retrievers.

Three query modes over the same index, so the evaluation can compare them:
  - keyword: Azure's own BM25 full-text search
  - vector:  nearest neighbours of the question's embedding (HNSW, cosine)
  - hybrid:  both at once, merged with Reciprocal Rank Fusion (RRF)
"""
import hashlib
import os
import re

from app.embeddings import EMBED_DIMS
from app.retrieval import SearchResult

VECTOR_FIELD = "contentVector"
VECTOR_PROFILE = "ask-barry-hnsw-profile"
HNSW_CONFIG = "ask-barry-hnsw"
MODES = ("keyword", "vector", "hybrid")
RETURN_FIELDS = ["id", "chunk_id", "repo", "path", "heading", "anchor", "url", "commit_sha", "content_hash", "content"]


_SUBJECT_NAME = re.compile(r"\bbarry(?:'s|s)?\b", re.IGNORECASE)


def keyword_query(query):
    """Drop the subject's name from the keyword part of a query.

    Every question mentions Barry and every doc is about Barry, so the name
    carries no information for ranking; worse, the project's own name
    ("Ask Barry") made keyword search favour this repo's README. BM25
    already ignores it as a stopword; this keeps Azure keyword/hybrid
    consistent. The vector part still embeds the full question.
    """
    cleaned = _SUBJECT_NAME.sub(" ", query)
    return re.sub(r"\s+", " ", cleaned).strip()


def doc_key(chunk_id):
    """Azure document keys allow only letters, digits, '_', '-' and '='; chunk_ids contain ':' '/' '#'."""
    return hashlib.sha1(chunk_id.encode("utf-8")).hexdigest()


def build_index(name, dims=EMBED_DIMS):
    """The index schema. Only public README text is stored."""
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration, SearchableField, SearchField, SearchFieldDataType,
        SearchIndex, SimpleField, VectorSearch, VectorSearchProfile,
    )
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="chunk_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="repo", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="path", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="heading", type=SearchFieldDataType.String),
        SimpleField(name="anchor", type=SearchFieldDataType.String),
        SimpleField(name="url", type=SearchFieldDataType.String),
        SimpleField(name="commit_sha", type=SearchFieldDataType.String),
        SimpleField(name="content_hash", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SearchField(
            name=VECTOR_FIELD,
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            hidden=True,                       # never returned in results: 1536 floats of noise
            vector_search_dimensions=dims,
            vector_search_profile_name=VECTOR_PROFILE,
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name=HNSW_CONFIG)],   # cosine metric by default
        profiles=[VectorSearchProfile(name=VECTOR_PROFILE, algorithm_configuration_name=HNSW_CONFIG)],
    )
    return SearchIndex(name=name, fields=fields, vector_search=vector_search)


def chunk_to_document(chunk, vector):
    """Map a chunk record (from chunks.jsonl) plus its embedding to an index document."""
    return {
        "id": doc_key(chunk["chunk_id"]),
        "chunk_id": chunk["chunk_id"],
        "repo": chunk["repo"],
        "path": chunk["path"],
        "heading": chunk.get("heading", ""),
        "anchor": chunk.get("anchor", ""),
        "url": chunk.get("url", ""),
        "commit_sha": chunk.get("commit_sha", ""),
        "content_hash": chunk["content_hash"],
        "content": chunk["text"],
        VECTOR_FIELD: vector,
    }


def document_to_chunk(doc):
    """Map a search hit back to the chunk shape the rest of the app uses."""
    return {
        "chunk_id": doc.get("chunk_id", ""),
        "repo": doc.get("repo", ""),
        "path": doc.get("path", ""),
        "heading": doc.get("heading", ""),
        "anchor": doc.get("anchor", ""),
        "url": doc.get("url", ""),
        "commit_sha": doc.get("commit_sha", ""),
        "content_hash": doc.get("content_hash", ""),
        "text": doc.get("content", ""),
    }


def plan_sync(chunks, existing):
    """Decide what ingestion must do.

    chunks:   current chunk records
    existing: {doc_id: content_hash} already in the index
    Returns (to_embed, unchanged_ids, to_delete_ids). Only new or changed
    chunks are embedded, so re-running ingestion costs nothing if nothing changed.
    """
    to_embed, unchanged = [], []
    current_ids = set()
    for c in chunks:
        key = doc_key(c["chunk_id"])
        current_ids.add(key)
        if existing.get(key) == c["content_hash"]:
            unchanged.append(key)
        else:
            to_embed.append(c)
    to_delete = sorted(set(existing) - current_ids)
    return to_embed, unchanged, to_delete


def search_client_from_env(index_name=None):
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    return SearchClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        index_name=index_name or os.environ.get("AZURE_SEARCH_INDEX", "ask-barry-chunks"),
        credential=AzureKeyCredential(os.environ["AZURE_SEARCH_API_KEY"]),
    )


def index_client_from_env():
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexClient
    return SearchIndexClient(os.environ["AZURE_SEARCH_ENDPOINT"], AzureKeyCredential(os.environ["AZURE_SEARCH_API_KEY"]))


class AzureSearchRetriever:
    """Same interface as BM25Retriever: search(query, k) -> list[SearchResult]."""

    def __init__(self, search_client, embedder=None, mode="hybrid"):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        if mode in ("vector", "hybrid") and embedder is None:
            raise ValueError(f"mode '{mode}' needs an embedder")
        self.client = search_client
        self.embedder = embedder
        self.mode = mode
        self.name = f"azure-{mode}"

    def search(self, query, k=5):
        if not query.strip():
            return []
        kwargs = {"top": k, "select": RETURN_FIELDS}
        if self.mode in ("vector", "hybrid"):
            from azure.search.documents.models import VectorizedQuery
            vector = self.embedder.embed([query])[0]
            # Ask the vector side for a wider candidate pool than k, so RRF has
            # enough overlap with the keyword results to fuse sensibly.
            knn = max(k, 20)
            kwargs["vector_queries"] = [VectorizedQuery(vector=vector, k_nearest_neighbors=knn, fields=VECTOR_FIELD)]
        search_text = None if self.mode == "vector" else (keyword_query(query) or query)
        hits = self.client.search(search_text=search_text, **kwargs)
        return [
            SearchResult(document_to_chunk(h), float(h.get("@search.score", 0.0)), rank)
            for rank, h in enumerate(list(hits)[:k], start=1)
        ]
