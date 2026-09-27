"""Stage 6: evaluate the ANSWERS end to end (retrieval + generation + honesty rules).

Usage (with AZURE_* values in .env; the index must be up to date):
    python -m scripts.evaluate_answers                 # all questions, print report
    python -m scripts.evaluate_answers --save          # also write docs/eval/<date>-answers.md
    python -m scripts.evaluate_answers --ids trap-01 profile-10   # a subset

What is measured per question:
  Answerable questions
    - answered:      the system gave a supported answer (not "no evidence")
    - cited_answer:  at least one CITED section is from an expected file and contains
                     an evidence phrase (the answer is backed by the right source)
    - faithful:      an LLM judge finds every claim supported by the cited text
    - checks:        fixed regression rules (must / must-not include phrases)
  Trap questions
    - no_false_claim: passes if the system refused, OR answered but (per the judge)
                      does not claim Barry has the skill (a grounded "no" is fine)

The judge is the same small model (gpt-4.1-mini) at temperature 0. A model judging
its own family is a known bias; the deterministic checks and citation test are there
so the headline numbers don't rest on the judge alone.
"""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

from scripts.evaluate_retrieval import load_golden

JUDGE_FAITHFUL = """You check whether an answer is fully supported by its sources.
Sources are excerpts from Barry Sisk's public GitHub documentation.
Return JSON: {"faithful": true or false, "unsupported": ["each claim not supported by the sources"]}
Mark faithful=false if ANY claim is missing from the sources, contradicts them, or presents
planned/future work as done (or done work as merely planned)."""

JUDGE_TRAP = """A question asks whether Barry has a particular skill or experience.
Decide whether the answer CLAIMS or IMPLIES that Barry has it.
A refusal, "no evidence", or a statement that he has not (yet) done it does NOT claim it.
Return JSON: {"claims_skill": true or false, "reason": "one short sentence"}"""


# ---------------------------------------------------------------------------
# Pure scoring logic (unit-tested)
# ---------------------------------------------------------------------------

def cited_answer_ok(answer, expected, evidence):
    """True if any cited source is from an expected file and its text contains an evidence phrase."""
    expected = set(expected)
    for src, text in zip(answer.sources, answer.cited_texts):
        if f"{src.repo}/{src.path}" in expected and any(p.lower() in (text or "").lower() for p in evidence):
            return True
    return False


def run_checks(answer_text, checks):
    """Deterministic regression rules. Returns list of failure messages (empty = pass)."""
    failures = []
    lower = answer_text.lower()
    for phrase in (checks or {}).get("must_include", []):
        if phrase.lower() not in lower:
            failures.append(f"missing '{phrase}'")
    for phrase in (checks or {}).get("must_not_include", []):
        if phrase.lower() in lower:
            failures.append(f"contains '{phrase}'")
    return failures


def parse_judge(raw):
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {"error": f"unparseable judge output: {str(raw)[:80]}"}


def score_question(q, answer, judge):
    """Score one question. `judge(kind, question, answer_text, sources_text)` returns a dict."""
    row = {"id": q["id"], "type": q["type"], "question": q["question"], "answer": answer.answer,
           "supported": answer.supported,
           "sources": [f"{s.repo}/{s.path} ({s.heading})" for s in answer.sources]}
    sources_text = "\n\n---\n\n".join(f"[{s.number}] {t}" for s, t in zip(answer.sources, answer.cited_texts))

    if q["type"] == "trap":
        if not answer.supported:
            row.update(no_false_claim=True, reason="refused")
        else:
            verdict = judge("trap", q["question"], answer.answer, sources_text)
            claims = verdict.get("claims_skill")
            row.update(no_false_claim=(claims is False), reason=verdict.get("reason") or verdict.get("error", ""))
        row["passed"] = row["no_false_claim"]
        return row

    row["answered"] = answer.supported
    row["cited_answer"] = answer.supported and cited_answer_ok(answer, q["expected"], q.get("evidence", []))
    row["check_failures"] = run_checks(answer.answer, q.get("checks")) if answer.supported else []
    if answer.supported:
        verdict = judge("faithful", q["question"], answer.answer, sources_text)
        row["faithful"] = verdict.get("faithful") is True
        row["unsupported"] = verdict.get("unsupported") or ([verdict["error"]] if "error" in verdict else [])
    else:
        row["faithful"] = None
        row["unsupported"] = []
    if q.get("checks") and not answer.supported:
        row["check_failures"] = ["did not answer"]
    row["passed"] = bool(row["answered"] and row["cited_answer"] and row["faithful"] and not row["check_failures"])
    return row


def summarise(rows):
    ans = [r for r in rows if r["type"] == "answerable"]
    traps = [r for r in rows if r["type"] == "trap"]
    answered = [r for r in ans if r["answered"]]

    def rate(items, key):
        return sum(1 for r in items if r.get(key)) / len(items) if items else 0.0

    return {
        "n_answerable": len(ans),
        "n_traps": len(traps),
        "answered": rate(ans, "answered"),
        "cited_answer": rate(ans, "cited_answer"),
        "faithful_of_answered": rate(answered, "faithful"),
        "checks_failed": sum(1 for r in ans if r.get("check_failures")),
        "trap_no_false_claim": rate(traps, "no_false_claim"),
        "passed": sum(1 for r in rows if r["passed"]),
        "total": len(rows),
    }


def render_report(rows, summary, model, when=None):
    when = when or date.today().isoformat()
    lines = [
        "# Answer evaluation (Stage 6)",
        "",
        f"Date: {when} · Model: {model} · Retrieval: Azure hybrid, top 8 · "
        f"Answerable: {summary['n_answerable']} · Traps: {summary['n_traps']}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Answered (answerable questions) | {summary['answered']:.0%} |",
        f"| Answer cites a section containing the answer | {summary['cited_answer']:.0%} |",
        f"| Faithful to cited sources (LLM judge, of answered) | {summary['faithful_of_answered']:.0%} |",
        f"| Regression checks failed | {summary['checks_failed']} |",
        f"| **Traps: no false claim** | **{summary['trap_no_false_claim']:.0%}** |",
        f"| Questions passing every check | {summary['passed']} of {summary['total']} |",
        "",
        "The judge is the same model family (gpt-4.1-mini), so the citation test and regression "
        "checks are deliberately deterministic. Sample sizes are small; one question is about 3 points.",
        "",
        "## Failures and notes",
        "",
    ]
    failures = [r for r in rows if not r["passed"]]
    if not failures:
        lines.append("None.")
    for r in failures:
        lines.append(f"### {r['id']} ({r['type']})")
        lines.append(f"- Answer: {r['answer'][:400]}")
        if r["type"] == "trap":
            lines.append(f"- Judge: {r.get('reason', '')}")
        else:
            lines.append(f"- answered={r['answered']} · cited_answer={r['cited_answer']} · faithful={r['faithful']}")
            if r.get("unsupported"):
                lines.append(f"- Unsupported claims: {'; '.join(map(str, r['unsupported']))[:400]}")
            if r.get("check_failures"):
                lines.append(f"- Check failures: {', '.join(r['check_failures'])}")
        lines.append(f"- Sources: {'; '.join(r['sources']) or 'none'}")
        lines.append("")
    lines += ["## All questions", "", "| ID | Type | Pass | Supported | Sources cited |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['type']} | {'✅' if r['passed'] else '❌'} | {r['supported']} | {len(r['sources'])} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Live run
# ---------------------------------------------------------------------------

def make_judge(client, deployment):
    def judge(kind, question, answer_text, sources_text):
        system = JUDGE_TRAP if kind == "trap" else JUDGE_FAITHFUL
        user = f"Question: {question}\n\nAnswer: {answer_text}\n\nSources:\n{sources_text or '(none)'}"
        resp = client.chat.completions.create(
            model=deployment, temperature=0, max_completion_tokens=300,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return parse_judge(resp.choices[0].message.content)
    return judge


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate answers end to end")
    parser.add_argument("--golden", default="eval/golden_set.json")
    parser.add_argument("--ids", nargs="*", help="only these question ids")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    import os

    from app.answering import answerer_from_env, azure_chat_client, azure_configured
    from app.embeddings import AzureOpenAIEmbedder, CachingEmbedder
    if not azure_configured():
        sys.exit("Azure settings missing in .env (run python -m scripts.check_azure)")

    questions = load_golden(args.golden)
    if args.ids:
        questions = [q for q in questions if q["id"] in set(args.ids)]
    client = azure_chat_client(max_retries=8)            # back off on 429s rather than fail
    embedder = CachingEmbedder(AzureOpenAIEmbedder(client=client))
    embedder.prewarm([q["question"] for q in questions])
    answerer = answerer_from_env(client=client, embedder=embedder)
    judge = make_judge(client, os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"])

    rows = []
    start = time.time()
    for i, q in enumerate(questions, 1):
        answer = answerer.ask(q["question"])
        row = score_question(q, answer, judge)
        rows.append(row)
        print(f"[{i:>2}/{len(questions)}] {'PASS' if row['passed'] else 'FAIL'}  {q['id']}")
    summary = summarise(rows)
    report = render_report(rows, summary, answerer.deployment)
    print("\n" + report)
    print(f"Took {time.time() - start:.0f}s")
    if args.save:
        out = Path("docs/eval") / f"{date.today().isoformat()}-answers.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Saved {out}")


if __name__ == "__main__":
    main()
