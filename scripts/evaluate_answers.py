"""Stage 6: evaluate the ANSWERS end to end (retrieval + generation + honesty rules).

Usage (with AZURE_* values in .env; the index must be up to date):
    python -m scripts.evaluate_answers                 # all questions, print report
    python -m scripts.evaluate_answers --save          # also write docs/eval/<date>-answers.md
    python -m scripts.evaluate_answers --ids trap-01 profile-10   # a subset
    python -m scripts.evaluate_answers --providers azure-openai anthropic gemini --save   # Stage 7d comparison
    python -m scripts.evaluate_answers --judge anthropic     # cross-check the judge's own bias

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
import re
import sys
import time
from datetime import date
from pathlib import Path

from scripts.evaluate_retrieval import load_golden

JUDGE_FAITHFUL = """You check whether an answer is supported by its sources.
Sources are excerpts from Barry Sisk's public GitHub documentation.

The sources come in two groups: CITED sources (the ones the answer cites) and OTHER retrieved
sources the answer saw but did not cite.
Split the answer into its factual claims. For each claim, give the shortest passage that supports it,
from a CITED source if possible, otherwise from an OTHER source, or null if nothing supports it.
- "support" must be copied word for word from the sources (at most 25 words; use "..." to
  join two separate pieces). Never reword it: it is checked against the sources automatically.
- The CLAIM may paraphrase: paraphrases and synonyms count as support ("daily" = "every day"; "uses X in VS Code" is
  supported by a diagram step "X in VS Code").
- A claim that something is PLANNED is supported by a source saying it will or can happen later.
- A claim that something is DONE is NOT supported by a source that only says it is planned, and vice versa.
- Wording like "Barry" vs "I" (the README author) is the same person.
- A general comment or conclusion the sources do not state (for example "this ensures security")
  is a claim with support null.

Return JSON: {"claims": [{"claim": "...", "support": "quoted passage or null"}]}"""

JUDGE_TRAP = """A question asks whether Barry has a particular skill or experience.
Decide whether the answer CLAIMS or IMPLIES that Barry has it.
A refusal, "no evidence", or a statement that he has not (yet) done it does NOT claim it.
Hedged wording that suggests he has it ("implying he has worked with X", "suggests experience with X") DOES claim it.
But an answer that clearly says the skill itself is NOT documented, and only describes a related activity the
sources do document, does NOT claim it.
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


def _norm(text):
    """Lowercase word tokens only: ignores markdown, HTML tags, ANSI codes, punctuation, emoji and spacing."""
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", " ", str(text or ""))       # ANSI colour codes the model sometimes emits
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text)                 # other control characters
    text = re.sub(r"<[^>]{0,40}>", " ", text.lower())
    return " " + " ".join(re.findall(r"\w+", text)) + " "


def _fuzzy_in(q, hay, min_share=0.8):
    """True if at least min_share of the quote's words appear, in order, within a short window of the sources.

    Tolerates small rewordings by the judge ("Render auto-deploys the Docker container" vs
    "Render auto-deploys Docker container") but not invented content words.
    """
    need = max(3, int(len(q) * min_share + 0.999))
    window = len(q) * 2 + 2
    for start, word in enumerate(hay):
        if word not in q[:len(q) - need + 1]:
            continue
        matched, qi = 0, q.index(word, 0, len(q) - need + 1)
        for w in hay[start:start + window]:
            if qi < len(q) and w == q[qi]:
                matched, qi = matched + 1, qi + 1
            else:
                while qi < len(q) and w != q[qi] and w in q[qi + 1:]:
                    qi += 1                       # the judge added a word the sources don't have
                if qi < len(q) and w == q[qi]:
                    matched, qi = matched + 1, qi + 1
        if matched >= need:
            return True
    return False


def quote_in_sources(quote, sources_text):
    """True if every substantial piece of the judge's quote (split on "..." and line breaks) is in the sources.

    Matching is on whole words, ignoring formatting. Exact word sequences of 3+ words or 12+
    characters pass; otherwise 80%+ of a 5+ word fragment must appear in order nearby AND every content word
    (4+ letters) must occur in the sources, so a light rewording passes but new content doesn't.
    """
    haystack = _norm(sources_text)
    hay_words = haystack.split()
    vocab = set(hay_words)

    def found(frag):
        f = _norm(frag)
        words = f.split()
        if f in haystack:
            return True
        new_content = [w for w in words if len(w) >= 4 and w not in vocab]
        return len(words) >= 5 and not new_content and _fuzzy_in(words, hay_words)

    # The judge may join separate passages with "..." or a line break: every substantial piece must be found.
    pieces = [p for p in re.split(r"\.\.\.|…|\n", str(quote or ""))
              if len(_norm(p).split()) >= 3 or len(_norm(p).strip()) >= 12]
    return bool(pieces) and all(found(p) for p in pieces)


UNCITED = "true but uncited"


def faithfulness(verdict, sources_text=None, other_text=None):
    """Decide faithfulness from the judge's per-claim evidence, not from a bare yes/no.

    Returns (faithful, unsupported_claims). A claim counts as supported only if the
    judge quoted a supporting passage AND (when sources_text is given) that quote
    really appears in the sources, so the judge can't invent evidence.
    A quote found only in the retrieved-but-uncited sections (other_text) is still a failure,
    because readers can't check it, but it is labelled "true but uncited", not invented.
    Simple verdicts with a boolean 'faithful' key are still accepted (unit tests).
    """
    if "error" in verdict:
        return False, [verdict["error"]]
    claims = verdict.get("claims")
    if isinstance(claims, list) and claims:
        unsupported = []
        for c in claims:
            if not isinstance(c, dict):
                unsupported.append(str(c))
                continue
            support = str(c.get("support") or "").strip()
            if not support or support.lower() == "null":
                unsupported.append(c.get("claim", "?"))
            elif sources_text is not None and not quote_in_sources(support, sources_text):
                if other_text and quote_in_sources(support, other_text):
                    unsupported.append(f"{c.get('claim', '?')} ({UNCITED}: support is in a retrieved section the answer didn't cite)")
                    continue
                unsupported.append(f"{c.get('claim', '?')} (judge quoted \"{support[:150]}\", not found in sources)")
        return not unsupported, unsupported
    if "faithful" in verdict:
        return verdict["faithful"] is True, list(verdict.get("unsupported") or [])
    return False, ["judge returned no claims"]


def parse_judge(raw):
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {"error": f"unparseable judge output: {str(raw)[:80]}"}


def judge_sources(answer):
    """The cited sources exactly as the answering model saw them: repo/file and section label, then text.

    The label matters: answers may name the project or quote a section heading, and the judge
    must see the same context to check those claims.
    """
    return "\n\n---\n\n".join(
        f"[{s.number}] {s.repo}/{s.path} (section: {s.heading})\n{t}"
        for s, t in zip(answer.sources, answer.cited_texts))


def other_sources(answer):
    """Retrieved sections the answer didn't cite, labelled for the judge."""
    return "\n\n---\n\n".join(f"[other {i}] {t}" for i, t in enumerate(getattr(answer, "uncited_texts", []) or [], start=1))


def score_question(q, answer, judge):
    """Score one question. `judge(kind, question, answer_text, sources_text, other_text="")` returns a dict."""
    row = {"id": q["id"], "type": q["type"], "question": q["question"], "answer": answer.answer,
           "supported": answer.supported,
           "sources": [f"{s.repo}/{s.path} ({s.heading})" for s in answer.sources]}
    sources_text = judge_sources(answer)

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
        other_text = other_sources(answer)
        verdict = judge("faithful", q["question"], answer.answer, sources_text, other_text)
        row["faithful"], row["unsupported"] = faithfulness(verdict, sources_text, other_text)
    else:
        row["faithful"] = None
        row["unsupported"] = []
    row["uncited"] = sum(1 for u in row["unsupported"] if UNCITED in str(u))
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
        "answers_with_uncited": sum(1 for r in ans if r.get("uncited")),
        "trap_no_false_claim": rate(traps, "no_false_claim"),
        "passed": sum(1 for r in rows if r["passed"]),
        "total": len(rows),
    }


def render_report(rows, summary, model, when=None):
    when = when or date.today().isoformat()
    lines = [
        "# Answer evaluation",
        "",
        f"Date: {when} · Model: {model} · Retrieval: Azure hybrid, top 8 · "
        f"Answerable: {summary['n_answerable']} · Traps: {summary['n_traps']}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Answered (answerable questions) | {summary['answered']:.0%} |",
        f"| Answer cites a section containing the answer | {summary['cited_answer']:.0%} |",
        f"| Faithful to cited sources (LLM judge, of answered) | {summary['faithful_of_answered']:.0%} |",
        f"| Answers with a true-but-uncited claim | {summary.get('answers_with_uncited', 0)} |",
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
                lines.append(f"- Unsupported claims: {'; '.join(map(str, r['unsupported']))[:900]}")
            if r.get("check_failures"):
                lines.append(f"- Check failures: {', '.join(r['check_failures'])}")
        lines.append(f"- Sources: {'; '.join(r['sources']) or 'none'}")
        lines.append("")
    lines += ["## All questions", "", "| ID | Type | Pass | Supported | Sources cited |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['type']} | {'✅' if r['passed'] else '❌'} | {r['supported']} | {len(r['sources'])} |")
    lines += ["", "## All answers (for human review)", ""]
    for r in rows:
        note = f" (judge: {r['reason']})" if r["type"] == "trap" and r.get("reason") and r["reason"] != "refused" else ""
        lines.append(f"- **{r['id']}** {'✅' if r['passed'] else '❌'} {r['question']}")
        lines.append(f"  - {r['answer'][:500]}{note}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Live run
# ---------------------------------------------------------------------------

def make_judge(provider):
    """LLM judge on any provider (app.providers): same prompts and scoring code for all of them."""
    def judge(kind, question, answer_text, sources_text, other_text=""):
        system = JUDGE_TRAP if kind == "trap" else JUDGE_FAITHFUL
        user = f"Question: {question}\n\nAnswer: {answer_text}\n\nCITED sources:\n{sources_text or '(none)'}"
        if kind != "trap":
            user += f"\n\n===\n\nOTHER retrieved sources (not cited by the answer):\n{other_text or '(none)'}"
        raw = provider.generate([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                max_tokens=1500)
        return parse_judge(raw)
    return judge


class CachingRetriever:
    """Retrieve once per question, so every provider answers from exactly the same sections."""

    def __init__(self, retriever):
        self.retriever = retriever
        self.cache = {}

    def search(self, query, k=8):
        if (query, k) not in self.cache:
            self.cache[(query, k)] = self.retriever.search(query, k=k)
        return self.cache[(query, k)]


def error_row(q, message):
    """A question the provider failed on (API error, unparseable output). Counts as a failure, never a pass."""
    row = {"id": q["id"], "type": q["type"], "question": q["question"], "answer": f"(error) {message}",
           "supported": False, "sources": [], "passed": False, "error": message}
    if q["type"] == "trap":
        row.update(no_false_claim=False, reason=f"error: {message}")
    else:
        row.update(answered=False, cited_answer=False, faithful=None, unsupported=[], uncited=0,
                   check_failures=[f"error: {message}"])
    return row


MAX_CONSECUTIVE_ERRORS = 3


def run_provider(answerer, questions, judge, log=print, max_consecutive_errors=MAX_CONSECUTIVE_ERRORS):
    """Answer and score every question with one provider. Returns (rows, stats).

    After several errors in a row (bad key, wrong model, quota), the provider is skipped for the
    remaining questions instead of retrying each one: those count as errors, never as passes.
    """
    rows, seconds, tokens_in, tokens_out = [], [], [], []
    streak = 0
    for i, q in enumerate(questions, 1):
        if streak >= max_consecutive_errors:
            rows.append(error_row(q, "skipped: provider failed on the previous questions"))
            continue
        try:
            answer = answerer.ask(q["question"])
            usage = getattr(answerer.provider, "usage", None)
            if usage and answer.retrieved:
                seconds.append(usage.seconds)
                tokens_in.append(usage.input_tokens)
                tokens_out.append(usage.output_tokens)
            row = score_question(q, answer, judge)
        except Exception as err:                        # one bad call shouldn't sink the whole comparison
            row = error_row(q, f"{type(err).__name__}: {err}"[:200])
        rows.append(row)
        streak = streak + 1 if row.get("error") else 0
        if streak == max_consecutive_errors:
            log(f"Stopping {getattr(answerer.provider, 'name', 'provider')}: {streak} errors in a row "
                f"(last: {row['error']}). Remaining questions are recorded as errors.")
        log(f"[{i:>2}/{len(questions)}] {'PASS' if row['passed'] else 'FAIL'}  {q['id']}"
            + (f"  ({row['error']})" if row.get("error") else ""))

    def median(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if xs else 0

    stats = {"errors": sum(1 for r in rows if r.get("error")), "median_seconds": median(seconds),
             "avg_tokens_in": sum(tokens_in) / len(tokens_in) if tokens_in else 0,
             "avg_tokens_out": sum(tokens_out) / len(tokens_out) if tokens_out else 0}
    return rows, stats


def render_comparison(results, judge_model, when=None):
    """results: list of (provider_name, model, rows, summary, stats), all on the same retrieved sections."""
    when = when or date.today().isoformat()
    lines = [
        "# Answer quality by model provider",
        "",
        f"Date: {when} · Same questions, same retrieved sections (Azure hybrid, top 8), same prompt and "
        f"honesty rules; only the answering model changes. Judge: {judge_model}.",
        "",
        "| Provider | Model | Passing | Faithful | True-but-uncited | Regression fails | Traps: no false claim | Errors | Median latency | Avg tokens in / out |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, model, rows, s, st in results:
        lines.append(
            f"| {name} | `{model}` | {s['passed']} of {s['total']} | {s['faithful_of_answered']:.0%} | "
            f"{s.get('answers_with_uncited', 0)} | {s['checks_failed']} | {s['trap_no_false_claim']:.0%} | "
            f"{st['errors']} | {st['median_seconds']:.1f}s | {st['avg_tokens_in']:.0f} / {st['avg_tokens_out']:.0f} |")
    lines += ["", "## Where the providers disagree", "",
              "| ID | " + " | ".join(name for name, *_ in results) + " |",
              "|---|" + "---|" * len(results)]
    by_id = [{r["id"]: r for r in rows} for _, _, rows, _, _ in results]
    for qid in by_id[0]:
        marks = ["✅" if b.get(qid, {}).get("passed") else "❌" for b in by_id]
        if len(set(marks)) > 1:
            lines.append(f"| {qid} | " + " | ".join(marks) + " |")
    lines += [
        "",
        "Notes:",
        "- One run per provider; single runs vary by a few questions, so treat small gaps as noise.",
        "- The judge is one fixed model for every provider. It may favour answers in its own style, especially "
        "from its own family; the citation test and regression checks are deterministic and unaffected.",
        "- Per-provider reports with every answer are saved next to this file.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    from app.providers import PROVIDER_NAMES
    parser = argparse.ArgumentParser(description="Evaluate answers end to end")
    parser.add_argument("--golden", default="eval/golden_set.json")
    parser.add_argument("--ids", nargs="*", help="only these question ids")
    parser.add_argument("--providers", nargs="+", default=["azure-openai"], choices=PROVIDER_NAMES,
                        help="answering model(s) to evaluate; several = a side-by-side comparison")
    parser.add_argument("--judge", default="azure-openai", choices=PROVIDER_NAMES, help="provider for the LLM judge")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    from app.answering import Answerer, answerer_from_env, azure_chat_client, azure_configured
    from app.embeddings import AzureOpenAIEmbedder, CachingEmbedder
    from app.providers import ProviderError, provider_from_env
    if not azure_configured():
        sys.exit("Azure settings missing in .env (run python -m scripts.check_azure)")

    questions = load_golden(args.golden)
    if args.ids:
        questions = [q for q in questions if q["id"] in set(args.ids)]
    client = azure_chat_client(max_retries=8)            # back off on 429s rather than fail
    try:
        providers = [provider_from_env(name, azure_client=client) for name in args.providers]
        judge_provider = provider_from_env(args.judge, azure_client=client)
    except ProviderError as err:
        sys.exit(f"{err} (run python -m scripts.check_providers)")
    embedder = CachingEmbedder(AzureOpenAIEmbedder(client=client))
    embedder.prewarm([q["question"] for q in questions])
    retriever = CachingRetriever(answerer_from_env(client=client, embedder=embedder).retriever)
    judge = make_judge(judge_provider)

    results, out_dir, today = [], Path("docs/eval"), date.today().isoformat()
    for provider in providers:
        print(f"\n=== {provider.name} ({provider.model}) ===")
        start = time.time()
        rows, stats = run_provider(Answerer(retriever, provider=provider), questions, judge)
        summary = summarise(rows)
        report = render_report(rows, summary, f"{provider.model} ({provider.name}); judge {judge_provider.model}")
        results.append((provider.name, provider.model, rows, summary, stats))
        print(f"{provider.name}: {summary['passed']} of {summary['total']} passing · took {time.time() - start:.0f}s")
        if len(providers) == 1:
            print("\n" + report)
        if args.save:
            out_dir.mkdir(parents=True, exist_ok=True)
            suffix = "" if provider.name == "azure-openai" and len(providers) == 1 else f"-{provider.name}"
            (out_dir / f"{today}-answers{suffix}.md").write_text(report, encoding="utf-8")
    if len(providers) > 1:
        comparison = render_comparison(results, f"{judge_provider.model} ({judge_provider.name})")
        print("\n" + comparison)
        if args.save:
            (out_dir / f"{today}-providers.md").write_text(comparison, encoding="utf-8")
    if args.save:
        print(f"Saved reports to {out_dir}/")


if __name__ == "__main__":
    main()
