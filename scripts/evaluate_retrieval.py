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
import statistics
from datetime import date
from pathlib import Path

from app.retrieval import BM25Retriever, load_chunks

KS = (1, 3, 5)


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
        if q["type"] == "trap" and q["expected"]:
            raise ValueError(f"{q['id']}: trap question must have no expected files")
        if q["type"] not in ("answerable", "trap"):
            raise ValueError(f"{q['id']}: unknown type {q['type']}")


def source_key(chunk):
    return f"{chunk['repo']}/{chunk['path']}"


def first_relevant_rank(results, expected):
    for r in results:
        if source_key(r.chunk) in expected:
            return r.rank
    return None


def evaluate(retriever, questions, k_max=max(KS)):
    rows = []
    for q in questions:
        results = retriever.search(q["question"], k=k_max)
        rows.append({
            "id": q["id"],
            "type": q["type"],
            "question": q["question"],
            "rank": first_relevant_rank(results, set(q["expected"])) if q["type"] == "answerable" else None,
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
        "| Metric | Value |",
        "|---|---|",
    ]
    for k in KS:
        lines.append(f"| Recall@{k} | {summary[f'recall@{k}']:.2f} |")
    lines += [
        f"| MRR | {summary['mrr']:.2f} |",
        f"| Median top score, answerable | {summary['answerable_top_score_median']:.2f} |",
        f"| Median top score, traps | {summary['trap_top_score_median']:.2f} |",
        f"| Traps that still matched something | {summary['traps_with_any_hit']} of {summary['n_traps']} |",
        "",
        "## Per question",
        "",
        "| ID | Rank of first correct file | Top score | Top result |",
        "|---|---|---|---|",
    ]
    for r in rows:
        rank = "trap" if r["type"] == "trap" else (r["rank"] or "miss")
        heading = r["top_heading"].replace("|", "/")[:60]
        lines.append(f"| {r['id']} | {rank} | {r['top_score']:.2f} | {r['top_source']} ({heading}) |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate retrieval against the golden set")
    parser.add_argument("--chunks", default="corpus/chunks.jsonl")
    parser.add_argument("--golden", default="eval/golden_set.json")
    parser.add_argument("--save", action="store_true", help="write docs/eval/<date>-<retriever>.md")
    args = parser.parse_args(argv)

    chunks = load_chunks(args.chunks)
    retriever = BM25Retriever(chunks)
    rows, summary = evaluate(retriever, load_golden(args.golden))
    report = render_report(retriever.name, rows, summary, len(chunks), corpus_sources(chunks))
    print(report)
    if args.save:
        out = Path("docs/eval") / f"{date.today().isoformat()}-{retriever.name}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Saved {out}")


if __name__ == "__main__":
    main()
