"""Run the job-ad evidence agent on one job advertisement, or on a folder of them (Stage 8).

Usage (with the AZURE_* settings in .env):
    python -m scripts.job_agent path/to/job_ad.txt            # prints the evidence map
    pbpaste | python -m scripts.job_agent -                    # macOS: job ad from the clipboard
    python -m scripts.job_agent job_ad.txt --save              # also writes reports/<date>-<name>.md and .json
    python -m scripts.job_agent ads/ --save                    # every .txt in ads/, one after another
    python -m scripts.job_agent job_ad.txt --framework langgraph            # ASK-70: the LangGraph version
    python -m scripts.job_agent job_ad.txt --framework langgraph --review   # approve the requirements first

In folder mode each report is named after its file (ads/accenture.txt -> reports/<date>-accenture.md),
so the reports line up with the companies. The .json holds the full verified report (for one-pagers).

The agent calls the ask_barry MCP server (local mode) once per requirement; see app/job_agent.py
for the guardrails.
"""
import argparse
import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:50] or "job"


def ad_files(target):
    """The job ads to run: one file, or every .txt in a folder (sorted)."""
    path = Path(target)
    if path.is_dir():
        files = sorted(p for p in path.glob("*.txt") if p.is_file())
        if not files:
            raise ValueError(f"No .txt job ads found in {path}/")
        return files
    return [path]


def save_report(report, markdown, name, out_dir=Path("reports")):
    out_dir.mkdir(exist_ok=True)
    stem = out_dir / f"{date.today().isoformat()}-{slugify(name)}"
    stem.with_suffix(".md").write_text(markdown, encoding="utf-8")
    stem.with_suffix(".json").write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return stem.with_suffix(".md")


async def run_many(items, run, render_markdown, save=False, trace=False):
    """items: [(name, text)]. Runs the agent on each in one event loop; a failure skips that ad only."""
    done = []
    for i, (name, text) in enumerate(items, 1):
        if len(items) > 1:
            print(f"\n=== [{i}/{len(items)}] {name} ===", flush=True)
        try:
            report, stats = await run(text)
        except ValueError as err:                  # empty or unusable ad
            print(f"Skipped {name}: {err}", flush=True)
            continue
        markdown = render_markdown(report)
        print(markdown)
        print(f"({stats['tool_calls']} tool calls, {stats['seconds']}s, guardrail actions: {report.guardrail_actions})")
        if trace:
            for n, call in enumerate(stats["tool_log"], 1):
                print(f"  [{n}] {call['question']!r} -> supported={call['supported']} links={len(call['urls'])}")
        if save:
            print(f"Saved {save_report(report, markdown, name)}")
        done.append((name, report))
    return done


def ask_reviewer(payload, read=input):
    """--review: show the planned requirements and ask which to drop (Enter keeps them all)."""
    print(f"\nPlanned requirements for {payload.get('role_title') or 'this ad'}:")
    for i, req in enumerate(payload["requirements"], 1):
        print(f"  {i:>2}. [{req['kind']}] {req['requirement']}  ->  {req['question']}")
    return read("Enter to check them all, or the numbers to drop (e.g. 3,5): ")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Map job ads to evidence in Barry's public docs")
    parser.add_argument("job_ad", help="a job ad .txt file, a folder of them, or - to read from stdin")
    parser.add_argument("--save", action="store_true", help="write each report to reports/ (.md and .json)")
    parser.add_argument("--trace", action="store_true", help="also print every tool call and result")
    parser.add_argument("--framework", choices=("agent-framework", "langgraph"), default="agent-framework",
                        help="which implementation of the agent to run (ASK-70)")
    parser.add_argument("--review", action="store_true",
                        help="LangGraph only: pause to approve or trim the requirement list before any lookups")
    args = parser.parse_args(argv)
    if args.review and args.framework != "langgraph":
        parser.error("--review needs --framework langgraph")

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from app.answering import azure_configured
    from app.job_agent import render_markdown
    if args.framework == "langgraph":
        from functools import partial

        from app.job_agent_langgraph import run as run_langgraph
        run = partial(run_langgraph, review=ask_reviewer if args.review else None)
    else:
        from app.job_agent_runtime import run
    if not azure_configured():
        sys.exit("Azure settings missing in .env (run python -m scripts.check_azure)")

    try:
        if args.job_ad == "-":
            items = [("job-ad", sys.stdin.read())]
        else:
            items = [(p.stem, p.read_text(encoding="utf-8")) for p in ad_files(args.job_ad)]
    except (ValueError, OSError) as err:
        sys.exit(str(err))
    done = asyncio.run(run_many(items, run, render_markdown, save=args.save, trace=args.trace))
    if len(items) > 1:
        print(f"\nFinished {len(done)} of {len(items)} job ads.")
    if not done:
        sys.exit(1)


if __name__ == "__main__":
    main()
