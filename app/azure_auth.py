"""How Ask Barry signs in to Azure OpenAI and Azure AI Search (ASK-8).

Two modes, chosen by AZURE_AUTH_MODE:

  entra (default)  Microsoft Entra ID tokens from DefaultAzureCredential. No API keys.
                   Locally it uses your `az login`; on Render it uses a service principal
                   (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET). What the app may
                   do is decided by Azure role assignments (least privilege), not by a key
                   that unlocks everything.
  key              The old API keys (AZURE_OPENAI_API_KEY, AZURE_SEARCH_API_KEY). Kept only
                   for the scheduled index refresh in GitHub Actions until it moves to OIDC.

Tokens last about an hour; the credential caches and renews them, so most calls cost
nothing extra. Managed identity replaces the service principal once the app runs on Azure.
"""
import asyncio
import os
from functools import lru_cache

MODES = ("entra", "key")
DEFAULT_MODE = "entra"
# One scope covers Azure OpenAI on both *.openai.azure.com and *.cognitiveservices.azure.com.
COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"

BASE_SETTINGS = (
    "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_EMBED_DEPLOYMENT", "AZURE_OPENAI_CHAT_DEPLOYMENT",
    "AZURE_SEARCH_ENDPOINT",
)
KEY_SETTINGS = ("AZURE_OPENAI_API_KEY", "AZURE_SEARCH_API_KEY")


def auth_mode(env=None):
    env = os.environ if env is None else env
    mode = (env.get("AZURE_AUTH_MODE") or DEFAULT_MODE).strip().lower()
    if mode not in MODES:
        raise ValueError(f"AZURE_AUTH_MODE must be one of {MODES}, not {mode!r}")
    return mode


def required_settings(env=None):
    """Settings the app needs in the current mode. Entra mode needs no secrets in this list:
    the service principal's settings are read by azure-identity, and locally `az login` is enough."""
    return BASE_SETTINGS + (KEY_SETTINGS if auth_mode(env) == "key" else ())


@lru_cache(maxsize=1)
def credential():
    """One shared credential for the whole process, so its token cache is shared too."""
    from azure.identity import DefaultAzureCredential
    return DefaultAzureCredential()


@lru_cache(maxsize=1)
def _openai_token_provider():
    from azure.identity import get_bearer_token_provider
    return get_bearer_token_provider(credential(), COGNITIVE_SCOPE)


def openai_api_key(env=None):
    """What to pass as OpenAI(api_key=...): the key string, or a function returning a fresh token."""
    env = os.environ if env is None else env
    if auth_mode(env) == "key":
        return env["AZURE_OPENAI_API_KEY"]
    return _openai_token_provider()


def openai_async_api_key(env=None):
    """Same for AsyncOpenAI, which wants an async function. The sync provider is wrapped in a thread
    rather than using azure.identity.aio, so there is one token cache and no extra aiohttp dependency."""
    key = openai_api_key(env)
    if isinstance(key, str):
        return key

    async def token():
        return await asyncio.to_thread(key)
    return token


def search_credential(env=None):
    """Credential for SearchClient / SearchIndexClient."""
    env = os.environ if env is None else env
    if auth_mode(env) == "key":
        from azure.core.credentials import AzureKeyCredential
        return AzureKeyCredential(env["AZURE_SEARCH_API_KEY"])
    return credential()
