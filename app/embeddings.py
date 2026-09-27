"""Text embeddings: Azure OpenAI in production, a deterministic fake in tests.

An embedding turns text into a list of 1536 numbers such that texts with
similar *meaning* end up close together, even when they share no words
("contact" vs "get in touch"). That is what Stage 4 adds on top of BM25.
"""
import hashlib
import math
import os
import re

EMBED_DIMS = 1536
BATCH_SIZE = 64          # well under Azure's 2,048-inputs-per-request limit


def openai_base_url(endpoint):
    """Accept https://<name>.openai.azure.com[/openai/v1] and return the v1 base URL."""
    endpoint = endpoint.strip().rstrip("/")
    if endpoint.endswith("/openai/v1"):
        return endpoint + "/"
    return endpoint + "/openai/v1/"


class AzureOpenAIEmbedder:
    """Calls an Azure OpenAI embeddings deployment via the OpenAI v1-compatible endpoint."""

    def __init__(self, endpoint=None, api_key=None, deployment=None, client=None):
        self.deployment = deployment or os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"]
        if client is None:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key or os.environ["AZURE_OPENAI_API_KEY"],
                base_url=openai_base_url(endpoint or os.environ["AZURE_OPENAI_ENDPOINT"]),
            )
        self.client = client
        self.calls = 0            # API requests made (for cost reporting)

    def embed(self, texts):
        """Embed a list of strings, batching requests; returns vectors in the same order."""
        vectors = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start:start + BATCH_SIZE]
            resp = self.client.embeddings.create(model=self.deployment, input=batch)
            self.calls += 1
            ordered = sorted(resp.data, key=lambda d: d.index)
            vectors.extend(d.embedding for d in ordered)
        return vectors


class FakeEmbedder:
    """Deterministic stand-in for tests: a hashed bag-of-words, L2-normalised.

    Texts sharing words get similar vectors, which is enough to test the
    plumbing without network access or cost. It is NOT semantic.
    """

    def __init__(self, dims=EMBED_DIMS):
        self.dims = dims
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return [self._one(t) for t in texts]

    def _one(self, text):
        vec = [0.0] * self.dims
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            vec[h % self.dims] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class CachingEmbedder:
    """Wraps an embedder and remembers vectors per text.

    The evaluation asks the same 43 questions of the vector and hybrid
    retrievers; caching embeds each question once, and prewarm() does it in
    a single batched request, which halves cost and avoids rate limits.
    """

    def __init__(self, inner):
        self.inner = inner
        self.cache = {}

    @property
    def calls(self):
        return self.inner.calls

    def prewarm(self, texts):
        missing = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if missing:
            self.cache.update(zip(missing, self.inner.embed(missing)))

    def embed(self, texts):
        self.prewarm(texts)
        return [self.cache[t] for t in texts]
