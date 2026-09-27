"""Ask a question from the terminal, using the same pipeline as the website.

Usage (with AZURE_* values in .env, including AZURE_OPENAI_CHAT_DEPLOYMENT):
    python -m scripts.ask "How does Wall Inspector deploy to production?"
    python -m scripts.ask --show-context "Has Barry used Kubernetes?"
"""
import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ask Barry from the command line")
    parser.add_argument("question")
    parser.add_argument("--show-context", action="store_true", help="also list the retrieved sections")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    from app.answering import answerer_from_env, azure_configured
    if not azure_configured():
        sys.exit("Azure settings missing in .env (run python -m scripts.check_azure)")

    answerer = answerer_from_env()
    if args.show_context:
        for r in answerer.retriever.search(args.question, k=answerer.k):
            print(f"  [{r.rank}] {r.chunk['repo']}/{r.chunk['path']} :: {r.chunk['heading'][:70]}")
        print()
    answer = answerer.ask(args.question)
    print(("SUPPORTED" if answer.supported else "NO EVIDENCE") + f"  ({answer.retrieved} sections, {answer.model})\n")
    print(answer.answer + "\n")
    for s in answer.sources:
        print(f"  [{s.number}] {s.repo}/{s.path} ({s.heading})\n      {s.url}")


if __name__ == "__main__":
    main()
