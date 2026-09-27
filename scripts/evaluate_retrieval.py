"""Score a retriever against the golden question set.

Usage (after fetch_docs + chunk_corpus):
    python -m scripts.evaluate_retrieval                  # prints a report
    python -m scripts.evaluate_retrieval --save           # also writes docs/eval/<date>-bm25.md

Metrics (answerable questions only):
  - Recall@k: share of questions where a chunk from an expected file is in the top k.
  - MRR: mean of 1/rank of the first relevant chunk (0 if none in the top k).
Trap questions have no right file. Keyword search cannot refuse, so the report
records their top score next to the answerable ones: it shows whether a simple
score threshold could separate "no evidence" from "evidence" (it usually can't).
"""
import argparse
import json
import sys
import statistics
from datetime import date
from pathlib import Path

from app.retrieval import BM25Retriever, load_chunks

KS = (1, 3, 5, 8)   # 8 = candidate context size for the Stage 5 answering step


def load_golden(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_golden(data)
    return data["questions"]


def validate_golden(data):
    """Fail fast on a malformed golden set (also run in CI)."""
    ids = set()
    for q in data["questions"]:
        for field in ("id", "type", "question", "expected"):
            if field not in q:
                raise ValueError(f"{q.get('id', '?')}: missing '{field}'")
        if q["id"] in ids:
            raise ValueError(f"duplicate id {q['id']}")
        ids.add(q["id"])
        if q["type"] == "answerable" and not q["expected"]:
            raise ValueError(f"{q['id']}: answerable question needs expected files")
        if q["type"] == "answerable" and not q.get("evidence"):
            raise ValueError(f"{q['id']}: answerable question needs evidence phrases")
        if q["type"] == "trap" and q["expected"]:
            raise ValueError(f"{q['id']}: trap question must have no expected files")
        checks = q.get("checks")
        if checks is not None and (not isinstance(checks, dict)
                                   or set(checks) - {"must_include", "must_not_include"}):
            raise ValueError(f"{q['id']}: checks may only contain must_include / must_not_include")
        if q["type"] not in ("answerable", "trap"):
            raise ValueError(f"{q['id']}: unknown type {q['type']}")


def source_key(chunk):
    return f"{chunk['repo']}/{chunk['path']}"


def first_relevant_rank(results, expected):
    """File level: rank of the first result from an expected file."""
    for r in results:
        if source_key(r.chunk) in expected:
            return r.rank
    return None


def contains_evidence(chunk, evidence):
    text = chunk.get("text", "").lower()
    return any(phrase.lower() in text for phrase in evidence)


def first_section_rank(results, expected, evidence):
    """Section level: rank of the first result from an expected file that actually contains the answer."""
    for r in results:
        if source_key(r.chunk) in expected and contains_evidence(r.chunk, evidence):
            return r.rank
    return None


def check_evidence(questions, chunks):
    """Ids of answerable questions whose evidence no longer appears in the corpus (docs drifted)."""
    missing = []
    for q in questions:
        if q["type"] != "answerable":
            continue
        expected = set(q["expected"])
        if not any(source_key(c) in expected and contains_evidence(c, q["evidence"]) for c in chunks):
            missing.append(q["id"])
    return missing


def evaluate(retriever, questions, k_max=max(KS)):
    rows = []
    for q in questions:
        results = retriever.search(q["question"], k=k_max)
        rows.append({
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "rank": first_relevant_rank(results, set(q["expected"])) if q["type"] == "answerable" else None,
            "section_rank": (first_section_rank(results, set(q["expected"]), q.get("evidence", []))
                             if q["type"] == "answerable" else None),
            "top_score": results[0].score if results else 0.0,
            "top_source": source_key(results[0].chunk) if results else "-",
            "top_heading": results[0].chunk.get("heading", "") if results else "",
        })
    return rows, summarise(rows)


def summarise(rows):
    ans = [r for r in rows if r["type"] == "answerable"]
    traps = [r for r in rows if r["type"] == "trap"]
    n = len(ans) or 1
    summary = {f"recall@{k}": sum(1 for r in ans if r["rank"] and r["rank"] <= k) / n for k in KS}
    summary["mrr"] = sum(1 / r["rank"] for r in ans if r["rank"]) / n
    for k in KS:
        summary[f"section_recall@{k}"] = sum(1 for r in ans if r.get("section_rank") and r["section_rank"] <= k) / n
    summary["section_mrr"] = sum(1 / r["section_rank"] for r in ans if r.get("section_rank")) / n
    summary["n_answerable"] = len(ans)
    summary["n_traps"] = len(traps)
    ans_scores = [r["top_score"] for r in ans]
    trap_scores = [r["top_score"] for r in traps]
    summary["answerable_top_score_median"] = statistics.median(ans_scores) if ans_scores else 0.0
    summary["trap_top_score_median"] = statistics.median(trap_scores) if trap_scores else 0.0
    summary["traps_with_any_hit"] = sum(1 for s in trap_scores if s > 0)
    return summary


def corpus_sources(chunks):
    """'repo@sha7' for every repo in the index, so a report says exactly what was searched."""
    seen = {}
    for c in chunks:
        seen.setdefault(c["repo"], (c.get("commit_sha") or "")[:7])
    return ", ".join(f"{repo}@{sha}" if sha else repo for repo, sha in sorted(seen.items()))


def render_report(retriever_name, rows, summary, n_chunks, sources=""):
    lines = [
        f"# Retrieval evaluation: {retriever_name}",
        "",
        f"Date: {date.today().isoformat()} · Chunks indexed: {n_chunks} · "
        f"Answerable questions: {summary['n_answerable']} · Trap questions: {summary['n_traps']}",
        "",
        f"Corpus: {sources}" if sources else "",
        "",
        "| Metric | File level | Section level (chunk contains the answer) |",
        "|---|---|---|",
    ]
    for k in KS:
        lines.append(f"| Recall@{k} | {summary[f'recall@{k}']:.2f} | {summary[f'section_recall@{k}']:.2f} |")
    lines += [
        f"| MRR | {summary['mrr']:.2f} | {summary['section_mrr']:.2f} |",
        "",
        "| Other | Value |",
        "|---|---|",
        f"| Median top score, answerable | {summary['answerable_top_score_median']:.2f} |",
        f"| Median top score, traps | {summary['trap_top_score_median']:.2f} |",
        f"| Traps that still matched something | {summary['traps_with_any_hit']} of {summary['n_traps']} |",
        "",
        "## Per question",
        "",
        "| ID | File rank | Section rank | Top score | Top result |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        if r["type"] == "trap":
            rank = section = "trap"
        else:
            rank, section = r["rank"] or "miss", r.get("section_rank") or "miss"
        heading = r["top_heading"].replace("|", "/")[:60]
        lines.append(f"| {r['id']} | {rank} | {section} | {r['top_score']:.2f} | {r['top_source']} ({heading}) |")
    return "\n".join(lines) + "\n"


RETRIEVERS = ("bm25", "azure-keyword", "azure-vector", "azure-hybrid")
# Stage 7d fixes for the self-crowding regression, compared against plain hybrid:
HYBRID_VARIANTS = {
    "azure-hybrid": {},
    "azure-hybrid-noname": {"name_free_vector": True},             # embed the question without "Barry"
    "azure-hybrid-cap3": {"per_repo_cap": 3},                      # at most 3 sections per repo in the top 8
    "azure-hybrid-noname-cap3": {"name_free_vector": True, "per_repo_cap": 3},
    "azure-hybrid-noname-cap4": {"name_free_vector": True, "per_repo_cap": 4},
}


def make_retriever(name, chunks, embedder=None):
    """Build a retriever by name. Azure ones read their settings from .env.

    Pass a shared (caching) embedder so several retrievers reuse one embedding per question.
    """
    if name == "bm25":
        return BM25Retriever(chunks)
    from app.azure_search import AzureSearchRetriever, search_client_from_env
    mode = name.split("-")[1]
    if mode in ("vector", "hybrid") and embedder is None:
        from app.embeddings import AzureOpenAIEmbedder, CachingEmbedder
        embedder = CachingEmbedder(AzureOpenAIEmbedder())
    options = HYBRID_VARIANTS.get(name, {})
    retriever = AzureSearchRetriever(search_client_from_env(), embedder if mode != "keyword" else None, mode=mode,
                                     **options)
    retriever.name = name
    return retriever


def render_comparison(results, n_chunks, sources):
    """One table comparing retrievers on the same questions."""
    n = next(iter(results.values()))[1]["n_answerable"] if results else 0
    lines = [
        "# Retrieval comparison",
        "",
        f"Date: {date.today().isoformat()} · Chunks: {n_chunks}",
        "",
        f"Corpus: {sources}",
        "",
        "## Section level (the retrieved chunk contains the answer)",
        "",
        "This is what matters for Stage 5: the answering model only sees the chunks retrieved.",
        "",
        "| Retriever | Recall@1 | Recall@3 | Recall@5 | Recall@8 | MRR | Not found in top 8 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, (rows, summary) in results.items():
        misses = [r["id"] for r in rows if r["type"] == "answerable" and not r.get("section_rank")]
        lines.append(
            f"| {name} | {summary['section_recall@1']:.2f} | {summary['section_recall@3']:.2f} | "
            f"{summary['section_recall@5']:.2f} | {summary['section_recall@8']:.2f} | "
            f"{summary['section_mrr']:.2f} | {', '.join(misses) or 'none'} |"
        )
    lines += [
        "",
        "## File level (a chunk from the right file)",
        "",
        "| Retriever | Recall@1 | Recall@3 | Recall@5 | Recall@8 | MRR | Not found in top 8 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, (rows, summary) in results.items():
        misses = [r["id"] for r in rows if r["type"] == "answerable" and not r["rank"]]
        lines.append(
            f"| {name} | {summary['recall@1']:.2f} | {summary['recall@3']:.2f} | "
            f"{summary['recall@5']:.2f} | {summary['recall@8']:.2f} | {summary['mrr']:.2f} | {', '.join(misses) or 'none'} |"
        )
    lines += [
        "",
        f"Sample: {n} answerable questions, so one question moves recall by about {1 / max(n, 1):.2f}. "
        "Treat small gaps as noise.",
        "",
        "Scores are not comparable across retrievers (BM25 scores vs Azure RRF scores), "
        "so trap questions are judged in Stage 5/6 by the answering step, not by a score threshold here.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate retrieval against the golden set")
    parser.add_argument("--chunks", default="corpus/chunks.jsonl")
    parser.add_argument("--golden", default="eval/golden_set.json")
    parser.add_argument("--retriever", choices=RETRIEVERS + tuple(HYBRID_VARIANTS) + ("all", "hybrid-variants"),
                        default="bm25", help="'hybrid-variants' compares the self-crowding fixes")
    parser.add_argument("--save", action="store_true", help="write reports to docs/eval/")
    parser.add_argument("--min-section-recall", type=float, default=None,
                        help="exit with an error if section-level recall@8 is below this (nightly guardrail)")
    args = parser.parse_args(argv)

    if args.retriever != "bm25":
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

    chunks = load_chunks(args.chunks)
    questions = load_golden(args.golden)
    sources = corpus_sources(chunks)
    stale = check_evidence(questions, chunks)
    if stale:
        print(f"WARNING: evidence phrases not found in the corpus for {', '.join(stale)}: "
              "the docs changed, so update eval/golden_set.json before trusting section-level scores.\n")
    if args.retriever == "all":
        names = RETRIEVERS
    elif args.retriever == "hybrid-variants":
        names = tuple(HYBRID_VARIANTS)
    else:
        names = (args.retriever,)

    embedder = None
    if any(n.startswith(("azure-vector", "azure-hybrid")) for n in names):
        from app.embeddings import AzureOpenAIEmbedder, CachingEmbedder
        embedder = CachingEmbedder(AzureOpenAIEmbedder())
        embedder.prewarm([q["question"] for q in questions])      # one batched request for all questions

    results = {}
    out_dir = Path("docs/eval")
    for name in names:
        retriever = make_retriever(name, chunks, embedder)
        rows, summary = evaluate(retriever, questions)
        results[name] = (rows, summary)
        report = render_report(name, rows, summary, len(chunks), sources)
        if len(names) == 1:
            print(report)
        if args.save:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{date.today().isoformat()}-{name}.md").write_text(report, encoding="utf-8")

    if len(names) > 1:
        comparison = render_comparison(results, len(chunks), sources)
        print(comparison)
        if args.save:
            (out_dir / f"{date.today().isoformat()}-comparison.md").write_text(comparison, encoding="utf-8")
    if embedder is not None:
        print(f"Embedding API calls for queries: {embedder.calls}")
    if args.save:
        print(f"Saved reports to {out_dir}/")
    if args.min_section_recall is not None:
        failures = below_threshold(results, args.min_section_recall)
        if failures:
            sys.exit("Retrieval quality check FAILED: " + "; ".join(failures))
        print(f"Retrieval quality check passed (section recall@8 >= {args.min_section_recall:.2f}).")


def below_threshold(results, minimum):
    """Retrievers whose section-level recall@8 is below `minimum`, with the questions they missed."""
    failures = []
    for name, (rows, summary) in results.items():
        if summary["section_recall@8"] < minimum:
            misses = [r["id"] for r in rows if r["type"] == "answerable" and not r.get("section_rank")]
            failures.append(f"{name} section recall@8 {summary['section_recall@8']:.2f} < {minimum:.2f} "
                            f"(missed: {', '.join(misses)})")
    return failures


if __name__ == "__main__":
    main()
