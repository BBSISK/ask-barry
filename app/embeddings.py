"""Text embeddings: Azure OpenAI in production, a deterministic fake in tests.

An embedding turns text into a list of 1536 numbers such that texts with
similar *meaning* end up close together, even when they share no words
("contact" vs "get in touch"). That is what Stage 4 adds on top of BM25.
"""
import hashlib
import math
import os
import re
import time

EMBED_DIMS = 1536
BATCH_SIZE = 16          # small requests: one batch of long sections must fit in a minute's token allowance
RATE_LIMIT_TRIES = 8     # ASK-53: on "429 rate limit", wait and retry rather than fail the nightly refresh
RATE_LIMIT_WAIT = 60     # seconds, when Azure doesn't say how long (it usually says 60)


def openai_base_url(endpoint):
    """Accept https://<name>.openai.azure.com[/openai/v1] and return the v1 base URL."""
    endpoint = endpoint.strip().rstrip("/")
    if endpoint.endswith("/openai/v1"):
        return endpoint + "/"
    return endpoint + "/openai/v1/"


class AzureOpenAIEmbedder:
    """Calls an Azure OpenAI embeddings deployment via the OpenAI v1-compatible endpoint."""

    def __init__(self, endpoint=None, api_key=None, deployment=None, client=None, sleep=time.sleep, log=print):
        self.deployment = deployment or os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"]
        if client is None:
            from openai import OpenAI

            from app.azure_auth import openai_api_key
            client = OpenAI(
                api_key=api_key or openai_api_key(),
                base_url=openai_base_url(endpoint or os.environ["AZURE_OPENAI_ENDPOINT"]),
            )
        self.client = client
        self.calls = 0            # API requests made (for cost reporting)
        self.sleep, self.log = sleep, log

    def embed(self, texts):
        """Embed a list of strings, batching requests; returns vectors in the same order."""
        vectors = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start:start + BATCH_SIZE]
            resp = self._create(batch)
            ordered = sorted(resp.data, key=lambda d: d.index)
            vectors.extend(d.embedding for d in ordered)
        return vectors

    def _create(self, batch):
        """One request, waiting out Azure's per-minute rate limit when it's hit (ASK-53).

        A big refresh (for example after new repos are published) can need more tokens than the deployment's
        per-minute allowance. Azure answers 429 with how long to wait; waiting is cheaper than failing."""
        for attempt in range(1, RATE_LIMIT_TRIES + 1):
            try:
                self.calls += 1
                return self.client.embeddings.create(model=self.deployment, input=batch)
            except Exception as err:
                if getattr(err, "status_code", None) != 429 or attempt == RATE_LIMIT_TRIES:
                    raise
                wait = retry_after(err)
                self.log(f"  embedding rate limit reached; waiting {wait}s (retry {attempt} of {RATE_LIMIT_TRIES - 1})")
                self.sleep(wait)


def retry_after(err, default=RATE_LIMIT_WAIT):
    """Seconds to wait, from the 429 response's Retry-After header when present (capped at 2 minutes)."""
    headers = getattr(getattr(err, "response", None), "headers", None) or {}
    try:
        seconds = int(float(headers.get("retry-after") or headers.get("Retry-After") or default))
    except (TypeError, ValueError):
        seconds = default
    return max(1, min(seconds, 120))


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
            h = int(hashlib.md5(word.encode(), usedforsecurity=False).hexdigest(), 16)
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
