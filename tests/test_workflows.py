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
    from app.azure_auth import required_settings
    assert "required_settings()" in inspect.getsource(ingest.main)
    in_key_mode = [n for n in required_settings({"AZURE_AUTH_MODE": "key"}) if n != "AZURE_OPENAI_CHAT_DEPLOYMENT"]
    assert sorted(in_key_mode) == sorted(INGEST_SETTINGS)


def test_refresh_workflow_uses_key_mode_explicitly_until_oidc():
    """Entra is the app's default; this job still has only keys, so it must say so or it would fail."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert text.count("AZURE_AUTH_MODE: key") == text.count("AZURE_SEARCH_API_KEY:") == 2


def test_refresh_workflow_checks_retrieval_with_the_production_retriever():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "--retriever azure-hybrid-noname --min-section-recall" in text
    assert text.index("python -m scripts.ingest") < text.index("python -m scripts.evaluate_retrieval")
