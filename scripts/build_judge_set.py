"""Stage 9a, step 1: build the claim set that the two judges and a human will all label.

    python -m scripts.build_judge_set                 # writes eval/judge_set.json (needs AZURE_* in .env)
    python -m scripts.build_judge_set --real 40 --near-miss 15

Real claims: sentences from Ask Barry's answers to the golden questions, each with the labelled sources
that answer cited. Near-miss claims: a real claim with ONE detail changed by the model so that it may no
longer be supported (e.g. another project, tool or number). Their origin is kept for analysis but never
shown while labelling, and the human label decides, not the origin.
"""
import argparse
import json
import random
import sys
from pathlib import Path

NEAR_MISS_RULES = """Rewrite the CLAIM so it stays plausible and similar in wording, but changes exactly ONE
factual detail (a project name, tool, number, or planned-vs-done) so that the SOURCES no longer support it.
Reply with JSON only: {"claim": "..."}"""


def near_miss(provider, claim, sources):
    raw = provider.generate([{"role": "system", "content": NEAR_MISS_RULES},
                             {"role": "user", "content": f"SOURCES:\n{sources[:6000]}\n\nCLAIM: {claim}"}], max_tokens=200)
    try:
        return json.loads(raw)["claim"].strip()
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def build(questions, answerer, provider, n_real, n_near, seed=7, log=print):
    from app.judges import split_claims
    from scripts.evaluate_answers import judge_sources
    pool = []
    for q in questions:
        answer = answerer.ask(q["question"])
        if not answer.supported:
            continue
        sources = judge_sources(answer)
        for claim in split_claims(answer.answer):
            pool.append({"question_id": q["id"], "question": q["question"], "claim": claim, "sources": sources})
        log(f"  {q['id']}: {len(pool)} claims so far")
    rng = random.Random(seed)
    rng.shuffle(pool)
    real = pool[:n_real]
    items = [dict(r, origin="answer") for r in real]
    for r in pool[n_real:]:
        if sum(1 for i in items if i["origin"] == "near-miss") >= n_near:
            break
        changed = near_miss(provider, r["claim"], r["sources"])
        if changed and changed != r["claim"]:
            items.append(dict(r, claim=changed, origin="near-miss"))
    rng.shuffle(items)
    for n, item in enumerate(items, 1):
        item.update(id=f"c{n:02d}", label=None)
    return items


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build eval/judge_set.json for Stage 9a")
    parser.add_argument("--golden", default="eval/golden_set.json")
    parser.add_argument("--out", default="eval/judge_set.json")
    parser.add_argument("--real", type=int, default=40)
    parser.add_argument("--near-miss", type=int, default=15)
    parser.add_argument("--force", action="store_true", help="overwrite an existing set (loses labels)")
    args = parser.parse_args(argv)
    out = Path(args.out)
    if out.exists() and not args.force:
        sys.exit(f"{out} exists (it may hold your labels). Use --force to rebuild.")
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from app.answering import answerer_from_env, azure_chat_client, azure_configured
    from app.providers import provider_from_env
    if not azure_configured():
        sys.exit("Azure settings missing in .env")
    golden = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    questions = [q for q in (golden["questions"] if isinstance(golden, dict) else golden) if q["type"] == "answerable"]
    client = azure_chat_client(max_retries=8)
    items = build(questions, answerer_from_env(client=client), provider_from_env("azure-openai", client),
                  args.real, args.near_miss)
    out.write_text(json.dumps({"version": 1, "items": items}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {len(items)} claims to {out}. Next: python -m scripts.label_claims")


if __name__ == "__main__":
    main()
