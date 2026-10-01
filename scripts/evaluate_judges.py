"""Stage 9a, step 3: measure both judges against your labels.

    python -m scripts.evaluate_judges            # prints the report (needs AZURE_* and CLOUDFLARE_* in .env)
    python -m scripts.evaluate_judges --save     # also writes docs/eval/<date>-judges.md
    python -m scripts.evaluate_judges --from-results --save   # re-score saved judge answers (no API calls)

If eval/adjudication.json exists, the report shows two views side by side: the blind labels, and the labels
after a documented adjudication of named claims (each with the source text that settles it). The adjudication
was done after seeing the judges' answers, so it can favour them: that's why both views are always printed.

For every claim you labelled "supported" or "not supported" (unsure ones are left out), both judges answer
the same question from the same labelled sources. Reported:
  accuracy           agreement with your label
  false support      the judge said "supported" when you said it isn't: the costly error for Ask Barry
  missed support     the judge said "not supported" when you said it is
  Cohen's kappa      agreement beyond chance (0 = chance, 1 = perfect)
  Jev threshold      accuracy / false support at cut-offs 0.3-0.8, and an "uncertain" band sent to a human
  cost and time      per judgement
"""
import argparse
import json
import statistics
import sys
from datetime import date
from pathlib import Path

THRESHOLDS = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
BAND = (0.35, 0.65)
JEV_PRICE = 0.042 / 1_000_000          # $ per input token (output free), Cloudflare listing Sept 2026
LLM_PRICE = 0.40 / 1_000_000           # $ per input token, gpt-4.1-mini (output is ~5 tokens here)


def final_label(it):
    """The reviewed label where there is one, otherwise the latest pass."""
    return it.get("label_final") or it.get("label")


def apply_adjudication(items, adjudication):
    """Copies of the items with adjudicated labels as their final label; the blind final label is kept."""
    by_id = {a["id"]: a for a in (adjudication or {}).get("items", [])}
    out = []
    for it in items:
        it = dict(it)
        if it["id"] in by_id:
            it["label_blind"] = final_label(it)
            it["label_final"] = by_id[it["id"]]["label"]
            it["adjudication_reason"] = by_id[it["id"]]["reason"]
        out.append(it)
    return out


def relabel(rows, items):
    """Saved judge answers scored against another set of labels (no API calls)."""
    labels = {it["id"]: it["label"] for it in labelled(items)}
    return [dict(r, label=labels[r["id"]]) for r in rows if r["id"] in labels]


def labelled(items):
    return [dict(it, label=final_label(it)) for it in items if final_label(it) in ("supported", "not_supported")]


def human_passes(items):
    """How accurate each labelling pass was against the reviewed labels (only once a review exists)."""
    if not any("label_final" in it for it in items):
        return None
    out = {}
    for key, name in (("label_pass1", "pass 1"), ("label", "pass 2")):
        pairs = [(it[key], final_label(it)) for it in items
                 if it.get(key) in ("supported", "not_supported") and final_label(it) in ("supported", "not_supported")]
        if pairs:
            out[name] = {"n": len(pairs), "accuracy": sum(a == b for a, b in pairs) / len(pairs),
                         "false_support": sum(1 for a, b in pairs if a == "supported" and b == "not_supported")}
    return {"passes": out, "reviewed": sum(1 for it in items if "label_final" in it)}


def confusion(truth, predicted):
    """truth / predicted: lists of bools (True = supported). None predictions count as wrong."""
    tp = sum(1 for t, p in zip(truth, predicted) if t and p is True)
    tn = sum(1 for t, p in zip(truth, predicted) if not t and p is False)
    fp = sum(1 for t, p in zip(truth, predicted) if not t and p is not False)     # false support
    fn = sum(1 for t, p in zip(truth, predicted) if t and p is not True)           # missed support
    return tp, tn, fp, fn


def kappa(truth, predicted):
    n = len(truth)
    if not n:
        return 0.0
    pred = [bool(p) for p in predicted]
    po = sum(t == p for t, p in zip(truth, pred)) / n
    pt, pp = sum(truth) / n, sum(pred) / n
    pe = pt * pp + (1 - pt) * (1 - pp)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def metrics(truth, predicted):
    tp, tn, fp, fn = confusion(truth, predicted)
    n = len(truth)
    return {"n": n, "accuracy": (tp + tn) / n if n else 0, "false_support": fp, "missed_support": fn,
            "kappa": kappa(truth, predicted)}


def sweep(truth, probs):
    return [{"threshold": t, **metrics(truth, [p >= t for p in probs])} for t in THRESHOLDS]


def band(truth, probs, low=BAND[0], high=BAND[1]):
    """Send Jev's unsure middle to a human; measure the rest."""
    sure = [(t, p) for t, p in zip(truth, probs) if p < low or p > high]
    m = metrics([t for t, _ in sure], [p > high for _, p in sure])
    return {"to_human": len(truth) - len(sure), "share_to_human": 1 - len(sure) / len(truth) if truth else 0, **m}


def run_judges(items, judges, log=print):
    rows = []
    for n, it in enumerate(items, 1):
        row = {"id": it["id"], "label": it["label"], "origin": it.get("origin"), "claim": it["claim"]}
        for key, judge in judges.items():
            try:
                row[key] = judge.judge(it["claim"], it["sources"])
            except Exception as err:                     # one failed call is a wrong answer, never a crash
                row[key] = {"supported": None, "p": None, "error": str(err)[:120], "seconds": 0, "input_tokens": 0}
        log(f"[{n:>2}/{len(items)}] {it['id']} label={it['label']:<13} "
            + "  ".join(f"{k}={_fmt(row[k])}" for k in judges))
        rows.append(row)
    return rows


def _fmt(r):
    if r.get("error"):
        return "ERROR"
    return f"{r['p']:.2f}" if r.get("p") is not None and r["p"] not in (0.0, 1.0) else str(r.get("supported"))


def self_agreement(items):
    """How often the human's second pass matched the first (only claims labelled y/n both times)."""
    pairs = [(it["label_pass1"], it["label"]) for it in items
             if it.get("label_pass1") in ("supported", "not_supported") and it.get("label") in ("supported", "not_supported")]
    if not pairs:
        return None
    same = sum(1 for a, b in pairs if a == b)
    return {"n": len(pairs), "same": same, "changed": len(pairs) - same,
            "kappa": kappa([a == "supported" for a, _ in pairs], [b == "supported" for _, b in pairs])}


def summarise(rows):
    truth = [r["label"] == "supported" for r in rows]
    out = {"n": len(rows), "supported": sum(truth), "not_supported": len(rows) - sum(truth)}
    for key, price in (("llm", LLM_PRICE), ("jev", JEV_PRICE)):
        preds = [r[key]["supported"] for r in rows]
        secs = [r[key]["seconds"] for r in rows if not r[key].get("error")]
        tokens = [r[key]["input_tokens"] for r in rows if not r[key].get("error")]
        out[key] = {**metrics(truth, preds), "errors": sum(1 for r in rows if r[key].get("error")),
                    "median_seconds": statistics.median(secs) if secs else 0,
                    "cost_per_1000": 1000 * price * statistics.mean(tokens) if tokens else 0}
    probs = [r["jev"]["p"] if r["jev"]["p"] is not None else 0.0 for r in rows]
    out["sweep"], out["band"] = sweep(truth, probs), band(truth, probs)
    out["both_wrong"] = [r["id"] for r in rows if r["llm"]["supported"] != (r["label"] == "supported")
                         and r["jev"]["supported"] != (r["label"] == "supported")]
    return out


def render(s, rows, when=None):
    when = when or date.today().isoformat()
    L = [f"# Two judges vs human labels (Stage 9a)", "",
         f"Date: {when} · {s['n']} claims labelled by hand ({s['supported']} supported, {s['not_supported']} not) · "
         "same claim and labelled sources for both judges", "",
         "| Judge | Accuracy | **False support** | Missed support | Cohen's kappa | Errors | Median time | Cost per 1,000 judgements |",
         "|---|---|---|---|---|---|---|---|"]
    for key, name in (("llm", "gpt-4.1-mini (LLM judge)"), ("jev", "Jev (threshold 0.5)")):
        m = s[key]
        L.append(f"| {name} | {m['accuracy']:.0%} | **{m['false_support']}** | {m['missed_support']} | {m['kappa']:.2f} | "
                 f"{m['errors']} | {m['median_seconds']:.1f}s | ${m['cost_per_1000']:.3f} |")
    b = s["band"]
    if s.get("human"):
        h = s["human"]
        L += ["", f"**Labels used:** reviewed final labels ({h['reviewed']} claims re-checked with full sources: every disputed "
              "claim plus a random sample of the rest). The human passes, scored against them:", "",
              "| Labeller | Accuracy | False support |", "|---|---|---|"]
        L += [f"| Barry, {name} | {m['accuracy']:.0%} | {m['false_support']} |" for name, m in h["passes"].items()]
    if s.get("self_agreement"):
        a = s["self_agreement"]
        L += ["", f"**Human self-agreement (two blind passes):** {a['same']} of {a['n']} claims labelled the same "
              f"({a['same'] / a['n']:.0%}), kappa {a['kappa']:.2f}; {a['changed']} changed. Scores above use the second pass."]
    L += ["", "False support = the judge accepted a claim you marked unsupported (the error that would let a wrong "
          "claim through). Kappa corrects agreement for chance.", "",
          "## Jev threshold", "", "| Threshold | Accuracy | False support | Missed support | Kappa |", "|---|---|---|---|---|"]
    L += [f"| {r['threshold']:.1f} | {r['accuracy']:.0%} | {r['false_support']} | {r['missed_support']} | {r['kappa']:.2f} |"
          for r in s["sweep"]]
    L += ["", f"**Uncertain band {BAND[0]}-{BAND[1]} sent to a human:** {b['to_human']} of {s['n']} claims "
          f"({b['share_to_human']:.0%}); on the rest Jev scores {b['accuracy']:.0%} with {b['false_support']} false support.", "",
          "## Where a judge disagreed with you", "", "| Claim | Your label | LLM | Jev p | Origin |", "|---|---|---|---|---|"]
    for r in rows:
        truth = r["label"] == "supported"
        if r["llm"]["supported"] != truth or r["jev"]["supported"] != truth:
            jp = "err" if r["jev"]["p"] is None else f"{r['jev']['p']:.2f}"
            L.append(f"| {r['id']}: {r['claim'].replace('|', '/')[:140]} | {r['label']} | {r['llm']['supported']} | {jp} | {r['origin']} |")
    return "\n".join(L) + "\n"


def render_adjudicated(blind, adjusted, adjudication, rows, when=None):
    """Both views first (blind and adjudicated), then the adjudication itself, then the full adjudicated report."""
    L = ["# Two judges vs human labels (Stage 9a, final)", "",
         "Two views of the same judge answers. **Blind** = my labels after two blind passes and a review with full "
         "sources, done without seeing the judges' answers. **Adjudicated** = the same labels with the claims below "
         "corrected after the judges disagreed with them, each settled by the source text. The adjudication saw the "
         "judges' answers, so it can favour them: read the two together.", "",
         "| Judge | Labels | Accuracy | **False support** | Missed support | Cohen's kappa |", "|---|---|---|---|---|---|"]
    for key, name in (("llm", "gpt-4.1-mini (LLM judge)"), ("jev", "Jev (threshold 0.5)")):
        for view, s in (("blind", blind), ("adjudicated", adjusted)):
            m = s[key]
            L.append(f"| {name} | {view} | {m['accuracy']:.0%} | **{m['false_support']}** | {m['missed_support']} | {m['kappa']:.2f} |")
    for view, s in (("blind", blind), ("adjudicated", adjusted)):
        if s.get("human"):
            L.append("")
            L.append(f"Barry's labelling passes against the {view} labels: " + "; ".join(
                f"{name} {m['accuracy']:.0%} ({m['false_support']} false support)" for name, m in s["human"]["passes"].items()))
    L += ["", f"## Adjudication ({adjudication.get('date', '')}, {adjudication.get('by', '')})", "",
          "| Claim | Blind label | Adjudicated | Why (from the sources) |", "|---|---|---|---|"]
    claims = {r["id"]: r["claim"] for r in rows}
    for a in adjudication["items"]:
        L.append(f"| {a['id']}: {claims.get(a['id'], '').replace('|', '/')[:110]} | {a.get('blind', '')} | {a['label']} | "
                 f"{a['reason'].replace('|', '/')} |")
    full = render(adjusted, relabel(rows, adjusted["_items"]), when)
    return "\n".join(L) + "\n\n---\n\n" + full.replace("# Two judges vs human labels (Stage 9a)", "# Full report, adjudicated labels", 1)


def report(rows, all_items, adjudication=None, when=None):
    """Score saved or fresh judge rows against the blind labels and, if given, the adjudicated ones."""
    blind_rows = relabel(rows, all_items)
    blind = summarise(blind_rows)
    blind.update(self_agreement=self_agreement(all_items), human=human_passes(all_items))
    if not adjudication:
        return render(blind, blind_rows, when)
    adj_items = apply_adjudication(all_items, adjudication)
    adjusted = summarise(relabel(rows, adj_items))
    adjusted.update(self_agreement=self_agreement(all_items), human=human_passes(adj_items), _items=adj_items)
    blind_by_id = {it["id"]: final_label(it) for it in all_items}
    adjudication = dict(adjudication, items=[dict(a, blind=blind_by_id.get(a["id"])) for a in adjudication["items"]])
    return render_adjudicated(blind, adjusted, adjudication, rows, when)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure the LLM judge and Jev against your labels")
    parser.add_argument("--set", default="eval/judge_set.json")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--adjudication", default="eval/adjudication.json")
    parser.add_argument("--from-results", action="store_true", help="re-score eval/judge_results.json, no API calls")
    args = parser.parse_args(argv)
    all_items = json.loads(Path(args.set).read_text(encoding="utf-8"))["items"]
    adj_path = Path(args.adjudication)
    adjudication = json.loads(adj_path.read_text(encoding="utf-8")) if adj_path.exists() else None
    if args.from_results:
        rows = json.loads(Path("eval/judge_results.json").read_text(encoding="utf-8"))
        _finish(report(rows, all_items, adjudication), rows, args.save, adjudication, write_rows=False)
        return
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from app.answering import azure_chat_client, azure_configured
    from app.jev import client_from_env, configured
    from app.judges import JevJudge, LLMJudge
    from app.providers import provider_from_env
    if not (azure_configured() and configured()):
        sys.exit("Needs the AZURE_* and CLOUDFLARE_* settings in .env")
    items = labelled(all_items)
    if not items:
        sys.exit("No labelled claims yet: run python -m scripts.label_claims")
    judges = {"llm": LLMJudge(provider_from_env("azure-openai", azure_chat_client(max_retries=8))),
              "jev": JevJudge(client_from_env())}
    rows = run_judges(items, judges)
    _finish(report(rows, all_items, adjudication), rows, args.save, adjudication)


def _finish(text, rows, save, adjudication, write_rows=True):
    print("\n" + text)
    if not save:
        return
    out = Path("docs/eval") / f"{date.today().isoformat()}-judges{'-final' if adjudication else ''}.md"
    out.write_text(text, encoding="utf-8")
    if write_rows:
        (Path("eval") / "judge_results.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out}" + (" and eval/judge_results.json" if write_rows else ""))


if __name__ == "__main__":
    main()
