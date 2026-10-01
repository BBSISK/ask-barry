"""Stage 9a, step 2: label each claim yourself (the ground truth both judges are measured against).

    python -m scripts.label_claims            # resumes where you stopped; saves after every answer
    python -m scripts.label_claims --second-pass   # label everything again, blind (first pass kept for comparison)
    python -m scripts.label_claims --review        # final check of disputed claims (+ a random sample of the rest)

For each claim you see the sources the answer cited, then the claim. Keys:
  y  supported: the sources state everything the claim says (paraphrase is fine)
  n  not supported: some part isn't in the sources (even if you know it's true!)
  u  unsure (left out of the scoring)     b  back one     q  save and quit
Judge only from the sources shown, not from what you know about your own work: that's what the judges do.
"""
import json
import sys
import textwrap
from pathlib import Path

KEYS = {"y": "supported", "n": "not_supported", "u": "unsure"}


def pending(items):
    return [i for i, it in enumerate(items) if it.get("label") is None]


def show(item, n, total, out=print):
    out("\n" + "=" * 88)
    out(f"Claim {n}/{total}   (question: {item['question']})")
    out("-" * 88 + "\nSOURCES the answer cited:\n")
    for block in item["sources"].split("\n\n---\n\n"):
        head, _, body = block.partition("\n")
        out("  " + head)
        out(textwrap.indent(textwrap.fill(" ".join(body.split()), 84), "    ") + "\n")   # full text: never truncate
    out("-" * 88)
    out("CLAIM:  " + textwrap.fill(item["claim"], 80, subsequent_indent="        "))
    out("\nCheck every name, number, tool, place and date in the claim against the sources above.")


def label_loop(items, save, ask=input, out=print):
    order = pending(items)
    pos = 0
    while pos < len(order):
        i = order[pos]
        show(items[i], len(items) - len(pending(items)) + 1, len(items), out)
        key = ask("\n[y] supported  [n] not supported  [u] unsure  [b] back  [q] quit > ").strip().lower()
        if key == "q":
            break
        if key == "b" and pos > 0:
            pos -= 1
            items[order[pos]]["label"] = None
            continue
        if key in KEYS:
            items[i]["label"] = KEYS[key]
            save()
            pos += 1
    done = sum(1 for it in items if it.get("label"))
    out(f"\n{done}/{len(items)} labelled." + (" All done: next, python -m scripts.evaluate_judges --save"
                                              if done == len(items) else " Run again to continue."))


def start_second_pass(items):
    """Keep pass-1 labels for the self-agreement check, and clear the labels for a fresh blind pass."""
    for it in items:
        if "label_pass1" not in it:
            it["label_pass1"] = it.get("label")
        it["label"] = None


def review_ids(items, results, sample=10, seed=11):
    """Claims to re-check with full sources: the two passes differ, or the label disagrees with BOTH judges,
    plus a random sample of the undisputed ones (so we don't only re-check where the judges disagree)."""
    import random
    by_id = {r["id"]: r for r in results}
    disputed = []
    for it in items:
        lab, r = it.get("label"), by_id.get(it["id"])
        passes_differ = it.get("label_pass1") in KEYS.values() and it.get("label_pass1") != lab
        both_judges_disagree = r is not None and lab in ("supported", "not_supported") and \
            r["llm"]["supported"] == r["jev"]["supported"] == (lab != "supported")
        if passes_differ or both_judges_disagree or lab == "unsure":
            disputed.append(it["id"])
    rest = [it["id"] for it in items if it["id"] not in disputed]
    return disputed + random.Random(seed).sample(rest, min(sample, len(rest)))


def review_loop(items, ids, save, ask=input, out=print):
    """Final labels, blind to the judges' answers and to your earlier labels; full sources shown."""
    todo = [it for it in items if it["id"] in ids and "label_final" not in it]
    for n, it in enumerate(todo, 1):
        show(it, n, len(todo), out)
        while True:
            key = ask("\nFINAL: [y] supported  [n] not supported  [q] save and quit > ").strip().lower()
            if key in ("y", "n", "q"):
                break
        if key == "q":
            break
        it["label_final"] = KEYS[key]
        it["review_reason"] = ask("Why, in a few words (optional, Enter to skip) > ").strip()
        save()
    left = sum(1 for it in items if it["id"] in ids and "label_final" not in it)
    out(f"\nReview: {len(ids) - left}/{len(ids)} done." + (" Next: python -m scripts.evaluate_judges --save"
                                                            if not left else " Run --review again to continue."))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    second = "--second-pass" in argv
    args = [a for a in argv if not a.startswith("--")]
    path = Path(args[0] if args else "eval/judge_set.json")
    if not path.exists():
        sys.exit(f"{path} not found: run python -m scripts.build_judge_set first")
    data = json.loads(path.read_text(encoding="utf-8"))
    if "--review" in argv:
        results_path = Path("eval/judge_results.json")
        if not results_path.exists():
            sys.exit("Run python -m scripts.evaluate_judges --save first (the review uses its results).")
        ids = review_ids(data["items"], json.loads(results_path.read_text(encoding="utf-8")))

        def save_review():
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{len(ids)} claims to review (disputed ones plus a random sample), full sources shown.")
        review_loop(data["items"], ids, save_review)
        return
    if second:
        if any("label_pass1" in it for it in data["items"]) and any(it.get("label") for it in data["items"]):
            sys.exit("A second pass is already under way: run without --second-pass to continue it.")
        start_second_pass(data["items"])

    def save():
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    label_loop(data["items"], save)


if __name__ == "__main__":
    main()
