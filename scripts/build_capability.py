"""Build capability.json (the ladder and evidence cards) from the live search index (ASK-42).

    python -m scripts.build_capability                      # writes data/capability.json + suggestions
    python -m scripts.build_capability --pack path/to/pack  # someone else's profile pack
    python -m scripts.build_capability --no-dates           # skip the GitHub "first committed" lookups

Runs nightly in GitHub Actions after the index refresh (signed in with OIDC, no keys). Cost: one small model
call per section checked (about 150 a night at most), a few cents.

Review suggestions:  data/capability_suggestions.json lists every drafted card example with its id. Copy the
ids you approve into profile/cards.yaml ("approved"), commit, and they go live after the next build.
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

from app.capability.builder import VOTES, TierJudge, StoryWriter, build_capability
from app.capability.pack import DEFAULT_PACK, PackError, load_pack
from app.capability.store import problems

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"


def load_env():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def github_first_commit(owner, token=None, timeout=20):
    """-> function(repo, path) giving the date (YYYY-MM-DD) the file was first committed, or None."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ask-barry-capability"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    @lru_cache(maxsize=None)
    def first(repo, path):
        oldest, page = None, 1
        try:
            while page <= 10:
                url = (f"{API}/repos/{owner}/{repo}/commits?path={urllib.parse.quote(path)}"
                       f"&per_page=100&page={page}")
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                    batch = json.loads(r.read().decode("utf-8"))
                if batch:
                    oldest = batch[-1]["commit"]["committer"]["date"][:10]
                if len(batch) < 100:
                    break
                page += 1
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as err:
            print(f"  first-commit lookup failed for {repo}/{path}: {err}", file=sys.stderr)
            return None
        return oldest
    return first


def live_parts():
    """The production retriever and the live chat model (same settings as the question box)."""
    import os
    from app.answering import answerer_from_env, azure_chat_client, azure_configured
    from app.providers import AzureOpenAIProvider
    if not azure_configured():
        sys.exit("Azure isn't configured (run python -m scripts.check_azure).")
    retriever = answerer_from_env().retriever
    provider = AzureOpenAIProvider(azure_chat_client(max_retries=6), os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"])
    return retriever, provider


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def summary_lines(capability):
    tiers = {t["level"]: t["label"] for t in capability["tiers"]}
    lines = [f"  {s['name']:<28} {tiers.get(s['tier'], 'Not evidenced')}  ({len(s['evidence'])} sources)"
             for s in capability["skills"]]
    lines += [f"  card {c['title']:<23} {'gap' if c['gap'] else str(len(c['stories'])) + ' approved'}"
              for c in capability["cards"]]
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build capability.json from the search index")
    parser.add_argument("--pack", default=str(DEFAULT_PACK), help="profile pack folder (default: profile/)")
    parser.add_argument("--out", default=str(ROOT / "data" / "capability.json"))
    parser.add_argument("--suggestions", default=str(ROOT / "data" / "capability_suggestions.json"))
    parser.add_argument("--no-dates", action="store_true", help="skip GitHub first-commit lookups")
    parser.add_argument("--previous", default=str(ROOT / "data" / "capability.json"),
                        help="last published build; approved examples keep their wording from it")
    parser.add_argument("--votes", type=int, default=VOTES, help="judge answers per section (median wins)")
    args = parser.parse_args(argv)

    load_env()
    try:
        pack = load_pack(args.pack)
    except PackError as err:
        sys.exit(str(err))
    retriever, provider = live_parts()
    first = None
    if not args.no_dates and pack.profile.get("github_owner"):
        import os
        first = github_first_commit(pack.profile["github_owner"], os.getenv("GITHUB_TOKEN"))

    previous = None
    if Path(args.previous).is_file():
        previous = json.loads(Path(args.previous).read_text(encoding="utf-8"))
        if problems(previous):
            print(f"Ignoring {args.previous}: it isn't a valid capability.json")
            previous = None
    capability, suggestions = build_capability(pack, retriever, TierJudge(provider, pack),
                                               StoryWriter(provider, pack), first_committed=first,
                                               votes=args.votes, previous=previous)
    found = problems(capability)
    if found:
        sys.exit("Refusing to write an invalid capability.json:\n  " + "\n  ".join(found[:10]))
    write_json(args.out, capability)
    write_json(args.suggestions, suggestions)
    print(f"Wrote {args.out} and {args.suggestions}")
    print("\n".join(summary_lines(capability)))


if __name__ == "__main__":
    main()
