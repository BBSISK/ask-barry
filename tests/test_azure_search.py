"""Offline tests for Stage 4: embeddings, index schema, ingestion sync and Azure retrievers.

Azure is replaced by small fakes, so CI never needs keys or network.
"""
import re
from types import SimpleNamespace

import pytest

from app.azure_search import (
    VECTOR_FIELD, AzureSearchRetriever, build_index, chunk_to_document, doc_key,
    document_to_chunk, plan_sync,
)
from app.embeddings import AzureOpenAIEmbedder, FakeEmbedder, openai_base_url
from scripts.ingest import sync


def make_chunk(i, text=None, repo="demo"):
    text = text or f"chunk number {i} about flask"
    return {"chunk_id": f"{repo}:README.md#{i}", "repo": repo, "path": "README.md", "heading": f"H{i}",
            "anchor": f"h{i}", "url": f"https://github.com/BBSISK/{repo}/blob/abc/README.md#h{i}",
            "commit_sha": "abc", "text": text, "content_hash": f"hash-{text}"}


# --- fakes -------------------------------------------------------------------

class FakeSearchClient:
    """Keeps documents in a dict; records the last search call."""

    def __init__(self, docs=None, hits=None):
        self.docs = dict(docs or {})
        self.hits = hits or []
        self.last_search = None

    def search(self, search_text=None, **kwargs):
        self.last_search = {"search_text": search_text, **kwargs}
        if search_text == "*" and "vector_queries" not in kwargs:
            return [{"id": k, "content_hash": d["content_hash"]} for k, d in self.docs.items()]
        return list(self.hits)

    def merge_or_upload_documents(self, documents):
        for d in documents:
            self.docs[d["id"]] = d
        return [SimpleNamespace(succeeded=True, key=d["id"]) for d in documents]

    def delete_documents(self, documents):
        for d in documents:
            self.docs.pop(d["id"], None)
        return [SimpleNamespace(succeeded=True, key=d["id"]) for d in documents]


class FakeOpenAI:
    """Mimics client.embeddings.create, returning items out of order like a real API may."""

    def __init__(self):
        self.requests = []
        self.embeddings = SimpleNamespace(create=self._create)

    def _create(self, model, input):
        self.requests.append((model, list(input)))
        data = [SimpleNamespace(index=i, embedding=[float(len(t))]) for i, t in enumerate(input)]
        return SimpleNamespace(data=list(reversed(data)))


# --- embeddings --------------------------------------------------------------

def test_azure_embedder_batches_and_keeps_order():
    fake = FakeOpenAI()
    emb = AzureOpenAIEmbedder(deployment="text-embedding-3-small", client=fake)
    texts = [f"t{'x' * i}" for i in range(130)]           # 130 texts -> 3 batches of <=64
    vectors = emb.embed(texts)
    assert [v[0] for v in vectors] == [float(len(t)) for t in texts]
    assert emb.calls == 3 and all(m == "text-embedding-3-small" for m, _ in fake.requests)


def test_fake_embedder_is_deterministic_and_normalised():
    e = FakeEmbedder(dims=64)
    a, b = e.embed(["Flask app on Render", "Flask app on Render"])
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-9


def test_openai_base_url_shared_helper():
    assert openai_base_url("https://x.openai.azure.com/") == "https://x.openai.azure.com/openai/v1/"


# --- index schema & mapping --------------------------------------------------

def test_doc_key_is_valid_azure_key_and_stable():
    key = doc_key("wall_inspector:README.md#3")
    assert re.fullmatch(r"[A-Za-z0-9_\-=]+", key)
    assert key == doc_key("wall_inspector:README.md#3") != doc_key("wall_inspector:README.md#4")


def test_index_schema_vector_field():
    index = build_index("ask-barry-chunks").as_dict()
    fields = {f["name"]: f for f in index["fields"]}
    vec = fields[VECTOR_FIELD]
    assert vec["dimensions"] == 1536
    assert vec["retrievable"] is False                     # vectors never sent back to the app
    assert fields["id"]["key"] is True
    assert fields["content"]["searchable"] is True
    assert index["vectorSearch"]["profiles"][0]["name"] == vec["vectorSearchProfile"]


def test_chunk_document_round_trip():
    c = make_chunk(1)
    doc = chunk_to_document(c, [0.5] * 3)
    assert doc["id"] == doc_key(c["chunk_id"]) and doc[VECTOR_FIELD] == [0.5] * 3
    back = document_to_chunk(doc)
    assert back["text"] == c["text"] and back["url"] == c["url"] and back["repo"] == "demo"


# --- sync planning & ingestion ----------------------------------------------

def test_plan_sync_embeds_only_new_or_changed_and_deletes_stale():
    c1, c2, c3 = make_chunk(1), make_chunk(2), make_chunk(3)
    existing = {doc_key(c1["chunk_id"]): c1["content_hash"],          # unchanged
                doc_key(c2["chunk_id"]): "old-hash",                  # changed
                "stale-id": "whatever"}                               # no longer in corpus
    to_embed, unchanged, to_delete = plan_sync([c1, c2, c3], existing)
    assert [c["chunk_id"] for c in to_embed] == [c2["chunk_id"], c3["chunk_id"]]
    assert unchanged == [doc_key(c1["chunk_id"])]
    assert to_delete == ["stale-id"]


def test_sync_is_idempotent_and_handles_removed_repos():
    client, emb = FakeSearchClient(), FakeEmbedder(dims=8)
    chunks = [make_chunk(i) for i in range(5)] + [make_chunk(9, repo="mathapp")]
    first = sync(chunks, client, emb, log=lambda *_: None)
    assert first == {"embedded": 6, "unchanged": 0, "deleted": 0}

    second = sync(chunks, client, emb, log=lambda *_: None)
    assert second == {"embedded": 0, "unchanged": 6, "deleted": 0}      # nothing re-embedded

    public_only = [c for c in chunks if c["repo"] != "mathapp"]           # repo made private
    third = sync(public_only, client, emb, log=lambda *_: None)
    assert third == {"embedded": 0, "unchanged": 5, "deleted": 1}
    assert all(d["repo"] != "mathapp" for d in client.docs.values())


def test_sync_dry_run_changes_nothing():
    client, emb = FakeSearchClient(), FakeEmbedder(dims=8)
    summary = sync([make_chunk(1)], client, emb, dry_run=True, log=lambda *_: None)
    assert summary["planned_embed"] == 1 and client.docs == {} and emb.calls == 0


def test_sync_raises_on_failed_upload():
    class Failing(FakeSearchClient):
        def merge_or_upload_documents(self, documents):
            return [SimpleNamespace(succeeded=False, key=d["id"], error_message="boom") for d in documents]
    with pytest.raises(RuntimeError, match="boom"):
        sync([make_chunk(1)], Failing(), FakeEmbedder(dims=8), log=lambda *_: None)


# --- retrievers --------------------------------------------------------------

HITS = [
    {"@search.score": 0.033, **chunk_to_document(make_chunk(1), [0.0])},
    {"@search.score": 0.016, **chunk_to_document(make_chunk(2), [0.0])},
]


@pytest.mark.parametrize("mode,expects_text,expects_vector", [
    ("keyword", True, False),
    ("vector", False, True),
    ("hybrid", True, True),
])
def test_retriever_modes_build_the_right_query(mode, expects_text, expects_vector):
    client = FakeSearchClient(hits=HITS)
    emb = FakeEmbedder(dims=8) if mode != "keyword" else None
    results = AzureSearchRetriever(client, emb, mode=mode).search("How does CI work?", k=2)
    call = client.last_search
    assert (call["search_text"] == "How does CI work?") is expects_text
    assert ("vector_queries" in call) is expects_vector
    assert call["top"] == 2
    assert [r.rank for r in results] == [1, 2]
    assert results[0].chunk["repo"] == "demo" and results[0].score == pytest.approx(0.033)


def test_retriever_respects_k_and_empty_query():
    client = FakeSearchClient(hits=HITS)
    r = AzureSearchRetriever(client, FakeEmbedder(dims=8), mode="hybrid")
    assert len(r.search("ci", k=1)) == 1
    assert r.search("   ") == []


def test_retriever_validates_mode_and_embedder():
    with pytest.raises(ValueError):
        AzureSearchRetriever(FakeSearchClient(), None, mode="semantic")
    with pytest.raises(ValueError):
        AzureSearchRetriever(FakeSearchClient(), None, mode="vector")


def test_evaluate_works_with_azure_retriever_interface():
    from scripts.evaluate_retrieval import evaluate
    client = FakeSearchClient(hits=HITS)
    questions = [{"id": "q", "type": "answerable", "question": "flask", "expected": ["demo/README.md"]}]
    rows, summary = evaluate(AzureSearchRetriever(client, FakeEmbedder(dims=8), mode="hybrid"), questions)
    assert rows[0]["rank"] == 1 and summary["recall@1"] == 1.0


def test_sync_treats_missing_index_as_empty():
    from azure.core.exceptions import ResourceNotFoundError

    class NoIndexYet(FakeSearchClient):
        def search(self, search_text=None, **kwargs):
            if search_text == "*":
                raise ResourceNotFoundError("The index 'ask-barry-chunks' was not found.")
            return super().search(search_text, **kwargs)

    summary = sync([make_chunk(1), make_chunk(2)], NoIndexYet(), FakeEmbedder(dims=8), dry_run=True, log=lambda *_: None)
    assert summary["planned_embed"] == 2


@pytest.mark.parametrize("question,expected", [
    ("Has Barry used Docker?", "Has used Docker?"),
    ("What is Barry's workflow?", "What is workflow?"),
    ("How can I contact barry", "How can I contact"),
    ("What is the Ask Barry project?", "What is the Ask project?"),
    ("Barrys tests", "tests"),
    ("barrymore stays", "barrymore stays"),      # only the whole word is removed
])
def test_keyword_query_drops_subject_name(question, expected):
    from app.azure_search import keyword_query
    assert keyword_query(question) == expected


def test_hybrid_sends_name_free_text_but_full_question_to_embedder():
    seen = []

    class RecordingEmbedder(FakeEmbedder):
        def embed(self, texts):
            seen.extend(texts)
            return super().embed(texts)

    client = FakeSearchClient(hits=HITS)
    AzureSearchRetriever(client, RecordingEmbedder(dims=8), mode="hybrid").search("Has Barry used Docker?")
    assert client.last_search["search_text"] == "Has used Docker?"
    assert seen == ["Has Barry used Docker?"]


def test_caching_embedder_embeds_each_text_once():
    from app.embeddings import CachingEmbedder
    inner = FakeEmbedder(dims=8)
    cache = CachingEmbedder(inner)
    cache.prewarm(["a b", "c d", "a b"])
    assert inner.calls == 1
    first = cache.embed(["c d", "a b"])
    assert inner.calls == 1                      # served from cache
    assert first == inner.embed(["c d", "a b"])
    cache.embed(["new text"])
    assert cache.calls == 3


def test_sync_refuses_a_run_that_would_wipe_most_of_the_index():
    from scripts.ingest import UnsafeSync
    client, emb = FakeSearchClient(), FakeEmbedder(dims=8)
    chunks = [make_chunk(i) for i in range(10)]
    sync(chunks, client, emb, log=lambda *_: None)
    with pytest.raises(UnsafeSync):                                    # partial fetch: 7 of 10 would go
        sync(chunks[:3], client, emb, log=lambda *_: None)
    assert len(client.docs) == 10                                      # nothing deleted
    with pytest.raises(UnsafeSync):
        sync([], client, emb, log=lambda *_: None)                     # empty fetch
    done = sync(chunks[:3], client, emb, log=lambda *_: None, allow_large_delete=True)
    assert done["deleted"] == 7                                        # explicit override works


# --- Stage 7d: self-crowding fixes -------------------------------------------

@pytest.mark.parametrize("question,expected", [
    ("How can I contact Barry?", "How can I contact ?"),
    ("Which programming languages does Barry know?", "Which programming languages does know?"),
    ("What is Barry's workflow?", "What is workflow?"),
    ("What is the Ask Barry project?", "What is the Ask Barry project?"),     # the project name is kept
    ("Does ask barry have a model card?", "Does ask barry have a model card?"),
    ("Barry", "Barry"),                                                        # never embed an empty string
])
def test_vector_query_drops_name_but_keeps_project_name(question, expected):
    from app.azure_search import vector_query
    assert vector_query(question) == expected


def _results(repos):
    from app.retrieval import SearchResult
    return [SearchResult({"repo": r, "chunk_id": f"{r}{i}"}, 1.0 / (i + 1), i + 1) for i, r in enumerate(repos)]


def test_diversify_caps_each_repo_and_keeps_rank_order():
    from app.azure_search import diversify
    ranked = _results(["ask-barry"] * 6 + ["BBSISK", "ask-barry", "BBSISK", "wall_inspector"])
    top = diversify(ranked, k=5, per_repo_cap=3)
    assert [r.chunk["repo"] for r in top] == ["ask-barry"] * 3 + ["BBSISK", "BBSISK"]
    assert [r.rank for r in top] == [1, 2, 3, 4, 5]


def test_diversify_tops_up_when_few_repos_match():
    from app.azure_search import diversify
    top = diversify(_results(["ask-barry"] * 6), k=5, per_repo_cap=3)
    assert len(top) == 5                                  # never returns fewer than k if results exist


def test_retriever_options_widen_pool_and_embed_name_free_text():
    seen = []

    class RecordingEmbedder(FakeEmbedder):
        def embed(self, texts):
            seen.extend(texts)
            return super().embed(texts)

    hits = [{"id": str(i), "chunk_id": f"c{i}", "repo": "ask-barry" if i < 6 else "BBSISK", "path": "README.md",
             "heading": "h", "url": "u", "text": "t", "@search.score": 1.0 / (i + 1)} for i in range(10)]
    client = FakeSearchClient(hits=hits)
    r = AzureSearchRetriever(client, RecordingEmbedder(dims=8), mode="hybrid", per_repo_cap=3, name_free_vector=True)
    out = r.search("How can I contact Barry?", k=5)
    assert seen == ["How can I contact ?"] and client.last_search["top"] == 30
    assert [x.chunk["repo"] for x in out].count("ask-barry") == 3


def test_default_retriever_behaviour_is_unchanged():
    client = FakeSearchClient(hits=HITS)
    AzureSearchRetriever(client, FakeEmbedder(dims=8), mode="hybrid").search("Has Barry used Docker?", k=8)
    assert client.last_search["top"] == 8


def test_hybrid_variants_are_selectable_for_evaluation(monkeypatch):
    import scripts.evaluate_retrieval as er
    monkeypatch.setattr("app.azure_search.search_client_from_env", lambda: FakeSearchClient(hits=HITS))
    r = er.make_retriever("azure-hybrid-noname-cap3", [], embedder=FakeEmbedder(dims=8))
    assert r.name == "azure-hybrid-noname-cap3" and r.per_repo_cap == 3 and r.name_free_vector


def test_below_threshold_names_the_missed_questions():
    from scripts.evaluate_retrieval import below_threshold
    rows = [{"id": "profile-09", "type": "answerable", "section_rank": None},
            {"id": "wall-01", "type": "answerable", "section_rank": 1}]
    results = {"azure-hybrid-noname": (rows, {"section_recall@8": 0.5})}
    assert below_threshold(results, 0.95) == ["azure-hybrid-noname section recall@8 0.50 < 0.95 (missed: profile-09)"]
    assert below_threshold({"x": (rows, {"section_recall@8": 1.0})}, 0.95) == []


def test_production_answerer_uses_the_name_free_vector(monkeypatch):
    import app.answering as answering
    monkeypatch.setattr("app.azure_search.search_client_from_env", lambda: FakeSearchClient(hits=HITS))
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini")
    a = answering.answerer_from_env(client=object(), embedder=FakeEmbedder(dims=8))
    assert a.retriever.name_free_vector is True and a.retriever.per_repo_cap is None
