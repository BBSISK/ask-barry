"""The nightly refresh workflow must pass every setting the ingest step needs, and stay read-only."""
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "refresh-index.yml"
INGEST_SETTINGS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_EMBED_DEPLOYMENT",
                   "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_API_KEY")


def test_refresh_workflow_passes_every_ingest_setting_from_secrets():
    text = WORKFLOW.read_text(encoding="utf-8")
    for name in INGEST_SETTINGS:
        assert f"{name}: ${{{{ secrets." in text, f"{name} missing from refresh-index.yml"


def test_refresh_workflow_runs_the_pipeline_in_order_and_is_read_only():
    text = WORKFLOW.read_text(encoding="utf-8")
    steps = [text.index(f"python -m scripts.{s}") for s in ("fetch_docs", "chunk_corpus", "ingest")]
    assert steps == sorted(steps)
    assert "contents: read" in text and "--allow-large-delete" not in text
    assert "schedule:" in text and "workflow_dispatch:" in text


def test_ingest_requires_exactly_these_settings():
    import inspect
    import scripts.ingest as ingest
    src = inspect.getsource(ingest.main)
    for name in INGEST_SETTINGS:
        assert f'"{name}"' in src
