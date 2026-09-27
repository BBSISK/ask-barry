# HDip Study Assistant

A question-answering app over my own Higher Diploma in Software Development course notes (Maynooth University). It is being built in stages to learn and demonstrate retrieval-augmented generation (RAG) with Azure AI Search and Azure OpenAI.

## Current status: Stage 0 (skeleton)

**What is live:** a Flask app with a health check, automated tests and CI, deployed on Render.
**What is not built yet:** search, embeddings and AI-generated answers. `/health` reports these as `false` until they exist.

| Stage | Scope | Status |
|---|---|---|
| 0 | Skeleton: Flask, tests, CI, Render deploy | In progress |
| 1 | Load and chunk notes (no AI) | Planned |
| 2 | Keyword search baseline + evaluation question set | Planned |
| 3 | Azure setup (Azure OpenAI, Azure AI Search) | Planned |
| 4 | Embeddings + hybrid search in Azure AI Search | Planned |
| 5 | Grounded answers with citations (RAG) | Planned |
| 6 | Answer-quality evaluation | Planned |
| 7 | Extras: multi-provider, Terraform, MCP tool, model card | Planned |

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

## Data and privacy

- The notes corpus lives in `corpus/`, which is gitignored. Only my own notes are used, never lecturers' slides or handouts.
- Secrets are environment variables only. The app refuses to start in production without `SECRET_KEY`.
