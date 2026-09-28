"""Run the job-ad evidence agent on one job advertisement (Stage 8).

Usage (with the AZURE_* settings in .env):
    python -m scripts.job_agent path/to/job_ad.txt            # prints the evidence map
    pbpaste | python -m scripts.job_agent -                    # macOS: job ad from the clipboard
    python -m scripts.job_agent job_ad.txt --save              # also writes reports/<date>-<role>.md

The agent calls the ask_barry MCP server (local mode) once per requirement; see app/job_agent.py
for the guardrails.
"""
import argparse
import asyncio
import re
import sys
from datetime import date
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Map a job ad to evidence in Barry's public docs")
    parser.add_argument("job_ad", help="text file with the job ad, or - to read from stdin")
    parser.add_argument("--save", action="store_true", help="write the report to reports/")
    parser.add_argument("--trace", action="store_true", help="also print every tool call and result")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from app.answering import azure_configured
    from app.job_agent import render_markdown
    from app.job_agent_runtime import run
    if not azure_configured():
        sys.exit("Azure settings missing in .env (run python -m scripts.check_azure)")

    text = sys.stdin.read() if args.job_ad == "-" else Path(args.job_ad).read_text(encoding="utf-8")
    try:
        report, stats = asyncio.run(run(text))
    except ValueError as err:
        sys.exit(str(err))
    markdown = render_markdown(report)
    print(markdown)
    print(f"({stats['tool_calls']} tool calls, {stats['seconds']}s, guardrail actions: {report.guardrail_actions})")
    if args.trace:
        for i, call in enumerate(stats["tool_log"], 1):
            print(f"  [{i}] {call['question']!r} -> supported={call['supported']} links={len(call['urls'])}")
    if args.save:
        slug = re.sub(r"[^a-z0-9]+", "-", report.role_title.lower()).strip("-")[:50] or "job"
        out = Path("reports") / f"{date.today().isoformat()}-{slug}.md"
        out.parent.mkdir(exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
        print(f"Saved {out}")


if __name__ == "__main__":
    main()
