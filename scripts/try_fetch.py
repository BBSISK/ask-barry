"""Try the job-ad link fetch on a real careers page (ASK-27 / ASK-29), and optionally keep the result as a test case.

    python -m scripts.try_fetch https://careers.example.com/jobs/123
    python -m scripts.try_fetch https://careers.example.com/jobs/123 --save tests/fixtures/firecrawl/example.json

Needs FIRECRAWL_API_KEY in .env (each page uses 5 Firecrawl credits). Runs the same checks as the live app:
blocked sites, robots.txt, public addresses only. --save keeps only what the tests need (the page's markdown,
the extracted fields and the status code), never the key, so the case can be replayed offline in CI.
"""
import argparse
import json
import sys
from pathlib import Path

from app.job_agent import MAX_JOB_AD_CHARS
from app.job_fetch import FetchError, FirecrawlFetcher, _post_json


def load_env():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch one job ad from a link with Firecrawl")
    parser.add_argument("url")
    parser.add_argument("--save", help="write a replayable fixture (markdown, fields, status) to this path")
    args = parser.parse_args(argv)

    load_env()
    import os
    key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not key:
        sys.exit("Set FIRECRAWL_API_KEY in .env first (https://firecrawl.dev, free plan).")

    seen = {}

    def post(url, payload, headers, timeout=None):
        status, body = _post_json(url, payload, headers)
        seen.update(status=status, body=body)
        return status, body

    try:
        ad = FirecrawlFetcher(key, post=post, max_chars=MAX_JOB_AD_CHARS).fetch(args.url)
    except FetchError as err:
        sys.exit(f"Refused ({err.status}): {err}")
    print(json.dumps({k: v for k, v in ad.items() if k != "text"}, indent=2, ensure_ascii=False))
    print(f"\n--- text for the box ({len(ad['text'])} chars) ---\n{ad['text'][:1500]}")

    if args.save:
        data = (seen.get("body") or {}).get("data") or {}
        fixture = {"url": args.url, "status": seen.get("status"),
                   "response": {"success": True, "data": {
                       "markdown": data.get("markdown", ""), "json": data.get("json") or {},
                       "metadata": {"statusCode": (data.get("metadata") or {}).get("statusCode")}}}}
        path = Path(args.save)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
