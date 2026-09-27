# Retrieval comparison

Date: 2026-09-27 · Chunks: 75

Corpus: BBSISK@509eed3, agentmath_showcase@82a0751, ask-barry@af435ab, inmytime-showcase@adecf68, my30words_showcase@59ea449, wall_inspector@bcd4662

## Section level (the retrieved chunk contains the answer)

This is what matters for Stage 5: the answering model only sees the chunks retrieved.

| Retriever | Recall@1 | Recall@3 | Recall@5 | Recall@8 | MRR | Not found in top 8 |
|---|---|---|---|---|---|---|
| azure-hybrid | 0.68 | 0.87 | 0.89 | 0.89 | 0.78 | profile-06, profile-09, profile-10, inmytime-05 |
| azure-hybrid-noname | 0.82 | 0.92 | 0.97 | 1.00 | 0.88 | none |
| azure-hybrid-cap3 | 0.68 | 0.87 | 0.95 | 1.00 | 0.80 | none |
| azure-hybrid-noname-cap3 | 0.82 | 0.92 | 0.97 | 0.97 | 0.88 | profile-09 |
| azure-hybrid-noname-cap4 | 0.82 | 0.92 | 0.97 | 0.97 | 0.88 | profile-09 |

## File level (a chunk from the right file)

| Retriever | Recall@1 | Recall@3 | Recall@5 | Recall@8 | MRR | Not found in top 8 |
|---|---|---|---|---|---|---|
| azure-hybrid | 0.79 | 0.92 | 0.92 | 0.95 | 0.86 | profile-06, profile-09 |
| azure-hybrid-noname | 0.87 | 0.97 | 0.97 | 1.00 | 0.92 | none |
| azure-hybrid-cap3 | 0.79 | 0.92 | 1.00 | 1.00 | 0.87 | none |
| azure-hybrid-noname-cap3 | 0.87 | 0.97 | 0.97 | 0.97 | 0.92 | profile-09 |
| azure-hybrid-noname-cap4 | 0.87 | 0.97 | 0.97 | 0.97 | 0.92 | profile-09 |

Sample: 38 answerable questions, so one question moves recall by about 0.03. Treat small gaps as noise.

Scores are not comparable across retrievers (BM25 scores vs Azure RRF scores), so trap questions are judged in Stage 5/6 by the answering step, not by a score threshold here.
