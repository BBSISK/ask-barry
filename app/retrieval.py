"""Keyword retrieval (BM25): the Stage 2 baseline.

BM25 ranks chunks by how often the query's words appear in them, weighted by
how rare each word is across the whole corpus (IDF) and normalised for chunk
length. It needs no AI, no network and no money, which makes it the honest
"before" number that the Azure vector/hybrid search in Stage 4 must beat.

All retrievers share one interface, `search(query, k) -> list[SearchResult]`,
so the evaluation script and (later) the app can swap them freely.
"""
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

TOKEN_RE = re.compile(r"[a-z0-9_]+")
STOPWORDS = frozenset("""
a an and are as at be been but by can could did do does for from had has have he
her his how i if in into is it its me my of on or our she so than that the their
them then there these they this to up was we were what when where which who why
will with would you your about any also barry barrys
""".split())


def tokenize(text):
    """Lowercase, split on non-word characters, drop stopwords, strip plural 's'.

    "barry" is treated as a stopword because nearly every question mentions
    him; it carries no information for ranking.
    """
    tokens = []
    for tok in TOKEN_RE.findall(text.lower()):
        if tok in STOPWORDS:
            continue
        if len(tok) > 4 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]                       # tests -> test, agents -> agent
        tokens.append(tok)
    return tokens


@dataclass
class SearchResult:
    chunk: dict      # the chunk record as written by scripts/chunk_corpus.py
    score: float
    rank: int        # 1-based


def load_chunks(path):
    """Read corpus/chunks.jsonl into a list of dicts."""
    with Path(path).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class BM25Retriever:
    """Okapi BM25 over chunk texts.

    k1 controls how quickly repeated words stop adding score;
    b controls how strongly long chunks are penalised.
    """

    name = "bm25"

    def __init__(self, chunks, k1=1.5, b=0.75):
        if not chunks:
            raise ValueError("BM25Retriever needs at least one chunk")
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_tokens = [Counter(tokenize(c["text"])) for c in chunks]
        self.doc_len = [sum(tf.values()) for tf in self.doc_tokens]
        self.avg_len = sum(self.doc_len) / len(self.doc_len) or 1.0
        n = len(chunks)
        df = Counter(term for tf in self.doc_tokens for term in tf)
        # BM25+ style IDF that is never negative, even for very common terms.
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def score(self, query_tokens, i):
        tf, length = self.doc_tokens[i], self.doc_len[i]
        total = 0.0
        for term in query_tokens:
            f = tf.get(term)
            if not f:
                continue
            norm = self.k1 * (1 - self.b + self.b * length / self.avg_len)
            total += self.idf[term] * f * (self.k1 + 1) / (f + norm)
        return total

    def search(self, query, k=5):
        q = tokenize(query)
        if not q:
            return []
        scored = [(self.score(q, i), i) for i in range(len(self.chunks))]
        scored = [(s, i) for s, i in scored if s > 0]
        scored.sort(key=lambda x: (-x[0], x[1]))           # stable tie-break by corpus order
        return [SearchResult(self.chunks[i], s, r) for r, (s, i) in enumerate(scored[:k], start=1)]
