# Retrieval comparison

Date: 2026-09-27 · Chunks: 59

Corpus: BBSISK@509eed3, agentmath_showcase@82a0751, ask-barry@8fa660a, inmytime-showcase@adecf68, my30words_showcase@59ea449, wall_inspector@bcd4662

| Retriever | Recall@1 | Recall@3 | Recall@5 | MRR | Misses (answerable) |
|---|---|---|---|---|---|
| bm25 | 0.83 | 0.94 | 0.94 | 0.88 | profile-02, profile-09 |
| azure-keyword | 0.89 | 0.94 | 1.00 | 0.92 | none |
| azure-vector | 0.80 | 0.97 | 1.00 | 0.88 | none |
| azure-hybrid | 0.86 | 0.97 | 0.97 | 0.91 | profile-09 |

Scores are not comparable across retrievers (BM25 scores vs Azure RRF scores), so trap questions are judged in Stage 5/6 by the answering step, not by a score threshold here.
