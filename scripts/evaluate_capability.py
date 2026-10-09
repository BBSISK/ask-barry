"""Check capability.json against hand labels, and two builds against each other (ASK-42).

    python -m scripts.evaluate_capability                         # data/capability.json vs eval/capability_labels.json
    python -m scripts.evaluate_capability --stability other.json  # also: do two builds give the same tiers?
    python -m scripts.evaluate_capability --save                  # also write docs/eval/<date>-capability.md

Pass criteria (ASK-42): at least 80% of labelled skills exactly right, no trap skill above "Not evidenced",
and, when a second build is given, the same tier for every skill in both builds.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_MATCH = 0.8


def score(capability, labels):
    tiers = {s["id"]: s["tier"] for s in capability["skills"]}
    names = {t["level"]: t["label"] for t in capability["tiers"]}
    rows, exact, close = [], 0, 0
    for sid, expected in labels["skills"].items():
        got = tiers.get(sid)
        ok = got == expected
        exact += ok
        close += got is not None and abs(got - expected) <= 1
        rows.append({"skill": sid, "expected": expected, "got": got, "ok": ok})
    traps = [sid for sid in labels.get("traps", []) if tiers.get(sid, 0) > 0]
    n = len(labels["skills"]) or 1
    return {"n": len(labels["skills"]), "exact": exact / n, "within_one": close / n, "rows": rows,
            "trap_failures": traps, "unlabelled": sorted(set(tiers) - set(labels["skills"])),
            "names": names}


def compare(a, b):
    """Skills whose tier differs between two builds."""
    tb = {s["id"]: s["tier"] for s in b["skills"]}
    return [{"skill": s["id"], "first": s["tier"], "second": tb.get(s["id"])}
            for s in a["skills"] if tb.get(s["id"]) != s["tier"]]


def passed(result, min_match=MIN_MATCH):
    return result["exact"] >= min_match and not result["trap_failures"]


def render(result, capability, labels, when=None, diffs=None):
    label = lambda t: "–" if t is None else f"{t} {result['names'].get(t, 'Not evidenced')}"   # noqa: E731
    lines = [f"# Capability ladder vs hand labels: {when or date.today().isoformat()}", "",
             f"Build generated {capability['generated_at']} · {result['n']} labelled skills", "",
             f"Labels: {labels.get('status', 'confirmed')}", "",
             f"- Exact tier: **{result['exact']:.0%}** (pass mark {MIN_MATCH:.0%})",
             f"- Within one tier: {result['within_one']:.0%}",
             f"- Trap skills claimed: **{len(result['trap_failures'])}** {result['trap_failures'] or ''}",
             *([f"- Stable across two builds: **{'yes' if not diffs else 'no'}**"
                + ("" if not diffs else " (" + ", ".join(f"{d['skill']} {d['first']} vs {d['second']}" for d in diffs) + ")")]
               if diffs is not None else []),
             f"- Result: **{'PASS' if passed(result) and not diffs else 'FAIL'}**", "",
             "| Skill | Expected | Built | |", "|---|---|---|---|"]
    lines += [f"| {r['skill']} | {label(r['expected'])} | {label(r['got'])} | {'✔' if r['ok'] else '✕'} |"
              for r in result["rows"]]
    if result["unlabelled"]:
        lines += ["", f"Not labelled yet: {', '.join(result['unlabelled'])}"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate capability.json")
    parser.add_argument("--capability", default=str(ROOT / "data" / "capability.json"))
    parser.add_argument("--labels", default=str(ROOT / "eval" / "capability_labels.json"))
    parser.add_argument("--stability", help="a second build to compare tiers with")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args(argv)

    capability = json.loads(Path(args.capability).read_text(encoding="utf-8"))
    diffs = None
    if args.stability:
        diffs = compare(capability, json.loads(Path(args.stability).read_text(encoding="utf-8")))
    labels = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    result = score(capability, labels)
    report = render(result, capability, labels, diffs=diffs)
    print(report)
    if args.save:
        out = ROOT / "docs" / "eval" / f"{date.today().isoformat()}-capability.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Saved {out}")
    sys.exit(0 if passed(result) and not diffs else 1)

if __name__ == "__main__":
    main()
