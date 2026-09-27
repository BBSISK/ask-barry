# Retrieval comparison

Date: 2026-09-27 · Chunks: 59

Corpus: BBSISK@509eed3, agentmath_showcase@82a0751, ask-barry@8fa660a, inmytime-showcase@adecf68, my30words_showcase@59ea449, wall_inspector@bcd4662

## Section level (the retrieved chunk contains the answer)

This is what matters for Stage 5: the answering model only sees the chunks retrieved.

| Retriever | Recall@1 | Recall@3 | Recall@5 | Recall@8 | MRR | Not found in top 8 |
|---|---|---|---|---|---|---|
| bm25 | 0.66 | 0.89 | 0.91 | 0.91 | 0.77 | profile-02, profile-09, inmytime-05 |
| azure-keyword | 0.74 | 0.89 | 0.94 | 0.94 | 0.81 | profile-09, inmytime-05 |
| azure-vector | 0.66 | 0.74 | 0.94 | 0.94 | 0.74 | profile-06, inmytime-05 |
| azure-hybrid | 0.80 | 0.89 | 0.94 | 1.00 | 0.86 | none |

## File level (a chunk from the right file)

| Retriever | Recall@1 | Recall@3 | Recall@5 | Recall@8 | MRR | Not found in top 8 |
|---|---|---|---|---|---|---|
| bm25 | 0.83 | 0.94 | 0.94 | 0.94 | 0.88 | profile-02, profile-09 |
| azure-keyword | 0.89 | 0.94 | 1.00 | 1.00 | 0.92 | none |
| azure-vector | 0.80 | 0.97 | 1.00 | 1.00 | 0.88 | none |
| azure-hybrid | 0.86 | 0.97 | 0.97 | 1.00 | 0.91 | none |

Sample: 35 answerable questions, so one question moves recall by about 0.03. Treat small gaps as noise.

Scores are not comparable across retrievers (BM25 scores vs Azure RRF scores), so trap questions are judged in Stage 5/6 by the answering step, not by a score threshold here.
