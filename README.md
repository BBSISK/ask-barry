# Ask Barry

A portfolio assistant that answers questions about my software projects ("Has Barry used Terraform?", "How does Wall Inspector's CI work?") using **only** the documentation in my public GitHub repositories, and cites the repo and file behind every answer. If the documentation doesn't support a claim, it says so rather than guessing.

It is being built in stages to learn and demonstrate retrieval-augmented generation (RAG) with Azure AI Search and Azure OpenAI.

## Current status: Stage 3 (Azure setup)

**What exists:** a Flask app with a health check, CI and Render deployment (Stage 0), plus offline scripts that fetch documentation from my public repos and split it into citable chunks (Stage 1), a keyword (BM25) search with an evaluation against a golden question set (Stage 2), and the Azure setup guide plus a smoke test for Azure OpenAI and Azure AI Search (Stage 3).
**What is not built yet:** search, embeddings and AI-generated answers. The live app does not use the chunks or the search yet, and `/health` reports these features as `false` until they exist.

| Stage | Scope | Status |
|---|---|---|
| 0 | Skeleton: Flask, tests, CI, Render deploy | Done |
| 1 | Fetch public repo READMEs/docs and split them into sections (no AI) | Done |
| 2 | Keyword search baseline + evaluation question set | Done |
| 3 | Azure setup (Azure OpenAI, Azure AI Search) | In progress: [guide](docs/azure-setup.md) |
| 4 | Embeddings + hybrid search in Azure AI Search | Planned |
| 5 | Grounded answers with citations (RAG) | Planned |
| 6 | Answer-quality evaluation, including refusal of unsupported claims | Planned |
| 7 | Extras: multi-provider, Terraform, MCP tool, model card | Planned |

## Sources

Only README and documentation files from my **public** GitHub repositories. No private repositories, source code, CV or personal details. Everything the assistant can see is already public.

## Build the document corpus (Stage 1)

```bash
python -m scripts.fetch_docs      # public, non-fork repos of BBSISK -> corpus/ + manifest.json
python -m scripts.chunk_corpus    # heading-aware chunks -> corpus/chunks.jsonl, with a summary
```

- **Selected files:** Markdown at each repo's root, anything under `docs/`, and README files at any depth. Forks, private repos, vendored folders and empty placeholders are skipped.
- **Excluded files:** `DEFAULT_EXCLUDED_PATHS` in `scripts/fetch_docs.py` leaves out public files that aren't evidence of my work, such as interview-rehearsal notes and domain reference catalogues. You can override it with `--exclude-paths`.
- **Pinned versions:** every file is fetched at an exact commit, so each chunk's GitHub link points at the version that was indexed.
- **Chunks:** each chunk carries its repo, file, heading breadcrumb and a link to the exact heading on GitHub (~500 tokens max, one paragraph of overlap, code blocks never split).
- `corpus/` is gitignored, so it can be rebuilt at any time. Set `GITHUB_TOKEN` (read-only) only if you hit the GitHub API rate limit.

## Evaluate retrieval (Stage 2)

```bash
python -m scripts.evaluate_retrieval          # print the report
python -m scripts.evaluate_retrieval --save   # also write docs/eval/<date>-bm25.md
```

- **Golden set:** `eval/golden_set.json` holds 35 questions with the file that answers each, plus 8 **trap** questions about skills my public docs don't evidence (e.g. Kubernetes, or "has he trained a YOLOv8 model?"). The final assistant must decline the traps.
- **Baseline (BM25, 45 chunks, 27 Sep 2026):** Recall@1 0.83 · Recall@3 0.94 · MRR 0.88. The full report is in [`docs/eval/2026-09-27-bm25.md`](docs/eval/2026-09-27-bm25.md).
- **What it shows:** the two misses are vocabulary mismatches ("studying for" vs "Higher Diploma", "contact" vs "Get in touch"). And 7 of 8 traps still match *something* on common words, so keyword scores alone can't tell "no evidence" from "evidence". These are the gaps that embeddings (Stage 4) and grounded answering (Stage 5) have to close.

## Run locally

Requires Python 3.12 (3.10+ should work).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # local settings; .env is gitignored
python -m pytest -v           # run the tests
flask --app wsgi run          # open http://127.0.0.1:5000
```

## Deployment

`render.yaml` defines the Render web service (free plan). Render generates `SECRET_KEY` itself, and deploys only after GitHub Actions CI passes (`autoDeployTrigger: checksPass`).

## Security

Secrets are environment variables only. The app refuses to start in production without `SECRET_KEY`.
