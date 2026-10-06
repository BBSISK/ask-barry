"""Stage 3 smoke test: prove the Azure resources are reachable with your sign-in.

Signs in the same way the app does (AZURE_AUTH_MODE, see app/azure_auth.py): Entra ID by default
(run `az login` first), or API keys with AZURE_AUTH_MODE=key.

Usage (after filling in the AZURE_* values in .env):
    python -m scripts.check_azure

It makes three tiny calls and prints PASS/FAIL for each:
  1. Azure OpenAI embeddings: embeds one short sentence, checks the vector size.
  2. Azure OpenAI chat: asks the chat deployment for a one-word reply.
  3. Azure AI Search: reads service statistics (no index needed yet).
Cost: a fraction of a cent. Secrets are never printed, only their last 4 characters.
"""
import os
import sys

REQUIRED = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_EMBED_DEPLOYMENT",
    "AZURE_SEARCH_ENDPOINT",
)
# Optional until Stage 5 (answers). Left blank, the chat check is skipped, e.g.
# while a quota request for the chat model is pending.
OPTIONAL = ("AZURE_OPENAI_CHAT_DEPLOYMENT",)
SECRET_NAMES = {"AZURE_OPENAI_API_KEY", "AZURE_SEARCH_API_KEY", "AZURE_CLIENT_SECRET"}
EXPECTED_EMBED_DIMS = 1536   # text-embedding-3-small

from app.azure_auth import KEY_SETTINGS, auth_mode, openai_api_key, search_credential  # noqa: E402
from app.embeddings import openai_base_url  # noqa: E402  (re-exported for tests)


def load_env():
    """Read .env if python-dotenv is installed (it is, via requirements-dev.txt)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def required(env):
    """REQUIRED, plus the two API keys in key mode. Entra mode needs no secrets here."""
    return REQUIRED + (KEY_SETTINGS if auth_mode(env) == "key" else ())


def missing_settings(env):
    return [name for name in required(env) if not env.get(name, "").strip()]


def describe(name, value):
    """Safe-to-print description of a setting: secrets show only their last 4 characters."""
    if name in SECRET_NAMES:
        return f"set (…{value[-4:]})" if len(value) >= 8 else "set (too short?)"
    return value


def check_embeddings(client, deployment):
    resp = client.embeddings.create(model=deployment, input="Barry builds Flask apps.")
    dims = len(resp.data[0].embedding)
    if dims != EXPECTED_EMBED_DIMS:
        raise RuntimeError(f"got {dims} dimensions, expected {EXPECTED_EMBED_DIMS} (is this text-embedding-3-small?)")
    return f"{dims}-dimension vector"


def check_chat(client, deployment):
    resp = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": "Reply with the single word: ready"}],
        max_completion_tokens=300,   # reasoning models spend some tokens thinking first
    )
    text = (resp.choices[0].message.content or "").strip()
    return f"model replied {text[:40]!r}" if text else "call succeeded (empty reply; fine for a smoke test)"


def check_search(endpoint, credential):
    from azure.search.documents.indexes import SearchIndexClient
    stats = SearchIndexClient(endpoint, credential).get_service_statistics()
    counters = stats["counters"] if isinstance(stats, dict) else stats.counters
    indexes = counters["index_counter"] if isinstance(counters, dict) else counters.index_counter
    usage = indexes["usage"] if isinstance(indexes, dict) else indexes.usage
    return f"reachable, {usage} index(es) so far"


def main():
    load_env()
    env = os.environ
    mode = auth_mode(env)
    if mode == "entra":
        who = "service principal (AZURE_CLIENT_ID)" if env.get("AZURE_CLIENT_ID") else "your az login"
        print(f"Sign-in: Entra ID, as {who}")
    else:
        print("Sign-in: API keys (AZURE_AUTH_MODE=key)")
    print("Settings:")
    for name in required(env) + OPTIONAL:
        value = env.get(name, "")
        blank = "not set (optional until Stage 5)" if name in OPTIONAL else "MISSING"
        print(f"  {name:<32} {describe(name, value) if value else blank}")
    missing = missing_settings(env)
    if missing:
        sys.exit(f"\nAdd these to .env first: {', '.join(missing)}")

    from openai import OpenAI
    client = OpenAI(api_key=openai_api_key(env), base_url=openai_base_url(env["AZURE_OPENAI_ENDPOINT"]))

    chat_deployment = env.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "").strip()
    checks = [
        ("Azure OpenAI embeddings", lambda: check_embeddings(client, env["AZURE_OPENAI_EMBED_DEPLOYMENT"])),
        ("Azure AI Search", lambda: check_search(env["AZURE_SEARCH_ENDPOINT"], search_credential(env))),
    ]
    if chat_deployment:
        checks.insert(1, ("Azure OpenAI chat", lambda: check_chat(client, chat_deployment)))
    failures = 0
    print()
    if not chat_deployment:
        print("SKIP  Azure OpenAI chat: AZURE_OPENAI_CHAT_DEPLOYMENT is blank (needed from Stage 5)")
    for label, fn in checks:
        try:
            print(f"PASS  {label}: {fn()}")
        except Exception as err:        # report every failure, don't stop at the first
            failures += 1
            print(f"FAIL  {label}: {type(err).__name__}: {str(err)[:300]}")
    if failures:
        sys.exit(f"\n{failures} check(s) failed. See docs/azure-setup.md, section 'Troubleshooting'.")
    if chat_deployment:
        print("\nAll Azure checks passed. Stage 3 is complete.")
    else:
        print("\nEmbeddings and Search passed: ready for Stage 4. Add the chat deployment before Stage 5.")


if __name__ == "__main__":
    main()
