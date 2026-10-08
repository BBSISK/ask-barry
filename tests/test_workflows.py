"""The nightly refresh workflow must pass every setting the ingest step needs, stay read-only,
and sign in to Azure with GitHub OIDC rather than stored keys (ASK-34)."""
import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "refresh-index.yml"
KEY_MODE_SETTINGS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_EMBED_DEPLOYMENT",
                     "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_API_KEY")
ENTRA_SETTINGS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_EMBED_DEPLOYMENT", "AZURE_SEARCH_ENDPOINT")


def test_refresh_workflow_passes_every_ingest_setting_from_secrets():
    text = WORKFLOW.read_text(encoding="utf-8")
    for name in ENTRA_SETTINGS:
        assert text.count(f"{name}: ${{{{ secrets.") == 2, f"{name} missing from a step in refresh-index.yml"


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
    def without_chat(env):
        return sorted(n for n in required_settings(env) if n != "AZURE_OPENAI_CHAT_DEPLOYMENT")
    assert without_chat({"AZURE_AUTH_MODE": "key"}) == sorted(KEY_MODE_SETTINGS)
    assert without_chat({"AZURE_AUTH_MODE": "entra"}) == sorted(ENTRA_SETTINGS)


def test_refresh_workflow_signs_in_with_oidc_and_holds_no_keys():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "id-token: write" in text
    assert "API_KEY" not in text and "ADMIN_KEY" not in text and "AZURE_AUTH_MODE: key" not in text
    assert text.count("AZURE_AUTH_MODE: entra") == 2
    # The IDs come from repository variables: identifiers, not secrets.
    assert "client-id: ${{ vars.AZURE_CLIENT_ID }}" in text and "secrets.AZURE_CLIENT_SECRET" not in text


def test_every_azure_step_has_a_fresh_sign_in_just_before_it():
    """GitHub's OIDC token is short-lived, so each Azure step gets its own azure/login."""
    steps = re.split(r"\n      - ", WORKFLOW.read_text(encoding="utf-8"))
    for i, step in enumerate(steps):
        if "AZURE_AUTH_MODE: entra" in step:
            assert "uses: azure/login@" in steps[i - 1], step.splitlines()[0]


def test_refresh_workflow_checks_retrieval_with_the_production_retriever():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "--retriever azure-hybrid-noname --min-section-recall" in text
    assert text.index("python -m scripts.ingest") < text.index("python -m scripts.evaluate_retrieval")
