"""ASK-8: Entra ID sign-in by default, API keys only when asked for. No network, no real credentials."""
import asyncio
import re
import time
from pathlib import Path

import pytest
from azure.core.credentials import AccessToken, AzureKeyCredential

from app import azure_auth
from app.answering import azure_configured

ROOT = Path(__file__).resolve().parents[1]
BASE = {name: "x" for name in azure_auth.BASE_SETTINGS}


class FakeCredential:
    """Stands in for DefaultAzureCredential and records which scopes were asked for."""

    def __init__(self):
        self.scopes = []

    def get_token(self, *scopes, **kwargs):
        self.scopes.extend(scopes)
        return AccessToken(f"token-{len(self.scopes)}", int(time.time()) + 3600)


@pytest.fixture
def fake_credential(monkeypatch):
    fake = FakeCredential()
    azure_auth.credential.cache_clear()
    azure_auth._openai_token_provider.cache_clear()
    monkeypatch.setattr(azure_auth, "credential", lambda: fake)
    yield fake
    azure_auth._openai_token_provider.cache_clear()


def test_entra_is_the_default_mode():
    assert azure_auth.auth_mode({}) == "entra"
    assert azure_auth.auth_mode({"AZURE_AUTH_MODE": " Key "}) == "key"


def test_unknown_mode_is_refused():
    with pytest.raises(ValueError):
        azure_auth.auth_mode({"AZURE_AUTH_MODE": "password"})


def test_entra_mode_needs_no_keys():
    assert azure_configured(BASE)
    assert not set(azure_auth.KEY_SETTINGS) & set(azure_auth.required_settings(BASE))


def test_key_mode_still_needs_both_keys():
    env = {**BASE, "AZURE_AUTH_MODE": "key"}
    assert not azure_configured(env)
    assert azure_configured({**env, "AZURE_OPENAI_API_KEY": "k1", "AZURE_SEARCH_API_KEY": "k2"})


def test_key_mode_passes_the_keys_through():
    env = {**BASE, "AZURE_AUTH_MODE": "key", "AZURE_OPENAI_API_KEY": "k1", "AZURE_SEARCH_API_KEY": "k2"}
    assert azure_auth.openai_api_key(env) == "k1"
    assert azure_auth.openai_async_api_key(env) == "k1"
    assert isinstance(azure_auth.search_credential(env), AzureKeyCredential)


def test_entra_mode_gives_openai_a_token_function_with_the_right_scope(fake_credential):
    provider = azure_auth.openai_api_key(BASE)
    assert callable(provider)
    assert provider().startswith("token-")
    assert fake_credential.scopes == [azure_auth.COGNITIVE_SCOPE]


def test_entra_tokens_are_cached_not_fetched_per_call(fake_credential):
    provider = azure_auth.openai_api_key(BASE)
    assert provider() == provider()
    assert len(fake_credential.scopes) == 1


def test_async_token_function_for_the_agent(fake_credential):
    token_fn = azure_auth.openai_async_api_key(BASE)
    assert asyncio.run(token_fn()).startswith("token-")


def test_entra_mode_gives_search_the_shared_credential(fake_credential):
    assert azure_auth.search_credential(BASE) is fake_credential


def test_no_module_reads_the_api_keys_directly():
    """Only app/azure_auth.py may touch the key settings, so key mode can't creep back in by accident."""
    pattern = re.compile(r"""environ\[["']AZURE_(OPENAI|SEARCH)_API_KEY|getenv\(["']AZURE_(OPENAI|SEARCH)_API_KEY""")
    offenders = [p.relative_to(ROOT).as_posix()
                 for folder in ("app", "scripts") for p in (ROOT / folder).rglob("*.py")
                 if p.name != "azure_auth.py" and pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


def test_az_login_gets_a_generous_timeout_for_slow_laptops():
    assert azure_auth.cli_timeout({}) == 60
    assert azure_auth.cli_timeout({"AZURE_CLI_TIMEOUT": "120"}) == 120
    assert azure_auth.cli_timeout({"AZURE_CLI_TIMEOUT": "3"}) == 10          # never below the library default
    assert azure_auth.cli_timeout({"AZURE_CLI_TIMEOUT": "soon"}) == 60
