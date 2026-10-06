"""Offline tests for the Azure smoke-test helpers (no network, no real keys)."""
from types import SimpleNamespace

import pytest

from scripts.check_azure import (
    REQUIRED,
    check_chat,
    check_embeddings,
    describe,
    missing_settings,
    openai_base_url,
)


def test_chat_deployment_is_optional():
    env = {name: "x" for name in REQUIRED}
    assert "AZURE_OPENAI_CHAT_DEPLOYMENT" not in REQUIRED
    assert missing_settings(env) == []


def test_missing_settings_lists_blank_and_absent():
    env = {name: "x" for name in REQUIRED}
    env["AZURE_SEARCH_ENDPOINT"] = "   "
    del env["AZURE_OPENAI_ENDPOINT"]
    assert missing_settings(env) == ["AZURE_OPENAI_ENDPOINT", "AZURE_SEARCH_ENDPOINT"]


def test_entra_mode_needs_no_keys():
    env = {name: "x" for name in REQUIRED}
    assert missing_settings(env) == []
    assert missing_settings({**env, "AZURE_AUTH_MODE": "entra"}) == []


def test_key_mode_needs_both_keys():
    env = {name: "x" for name in REQUIRED} | {"AZURE_AUTH_MODE": "key", "AZURE_SEARCH_API_KEY": "  "}
    assert missing_settings(env) == ["AZURE_OPENAI_API_KEY", "AZURE_SEARCH_API_KEY"]


def test_client_secret_is_never_printed_in_full():
    assert "SECRET" not in describe("AZURE_CLIENT_SECRET", "abcdSECRETxyz1234")


def test_secrets_are_never_printed_in_full():
    key = "abcdefgh12345678SECRET9f3a"
    shown = describe("AZURE_OPENAI_API_KEY", key)
    assert key not in shown
    assert shown.endswith("9f3a)")
    assert describe("AZURE_OPENAI_ENDPOINT", "https://x.openai.azure.com") == "https://x.openai.azure.com"


@pytest.mark.parametrize("endpoint", [
    "https://barry.openai.azure.com",
    "https://barry.openai.azure.com/",
    "https://barry.openai.azure.com/openai/v1",
    "https://barry.openai.azure.com/openai/v1/",
])
def test_openai_base_url_normalised(endpoint):
    assert openai_base_url(endpoint) == "https://barry.openai.azure.com/openai/v1/"


class FakeClient:
    def __init__(self, dims=1536, reply="ready"):
        self.embeddings = SimpleNamespace(create=lambda **kw: SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.0] * dims)]))
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))])))


def test_check_embeddings_accepts_1536_dims():
    assert "1536" in check_embeddings(FakeClient(), "embed")


def test_check_embeddings_rejects_wrong_model():
    with pytest.raises(RuntimeError, match="3072"):
        check_embeddings(FakeClient(dims=3072), "embed")


def test_check_chat_handles_empty_reply():
    assert "ready" in check_chat(FakeClient(), "chat")
    assert "empty reply" in check_chat(FakeClient(reply=None), "chat")
