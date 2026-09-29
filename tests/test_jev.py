"""Stage 9: Jev client (Cloudflare Workers AI), offline."""
import pytest

from app.jev import JevClient, choice, configured, noul, score
from app.providers import ProviderError

QUESTIONS = {"ok": noul("Is it supported?"), "team": choice("Which?", {"a": "A", "b": "B"}),
             "level": score("How much?", ["low", "high"])}
ANSWERS = {"ok": {"type": "noul", "noul": 0.9}, "team": {"type": "choice", "choice": "a", "confidence": 0.8},
           "level": {"type": "score", "score": 0.2, "confidence": 0.9}}


def fake_poster(status, body):
    calls = []

    def poster(url, payload, headers, **_):
        calls.append((url, payload, headers))
        return status, body
    poster.calls = calls
    return poster


def test_request_shape_and_cloudflare_result_wrapper():
    poster = fake_poster(200, {"success": True, "result": {"model": "jev-1.13.0", "answers": ANSWERS,
                                                           "usage": {"input_tokens": 50}}})
    client = JevClient("acct123", "tok", poster=poster)
    assert client.ask("some state", QUESTIONS) == ANSWERS
    url, payload, headers = poster.calls[0]
    assert url == "https://api.cloudflare.com/client/v4/accounts/acct123/ai/run"
    assert payload["model"] == "typesafe/jev" and payload["input"]["questions"]["ok"]["type"] == "noul"
    assert headers["Authorization"] == "Bearer tok" and client.usage == {"input_tokens": 50}


def test_errors_and_missing_answers_are_raised():
    with pytest.raises(ProviderError, match="HTTP 403"):
        JevClient("a", "t", poster=fake_poster(403, {"errors": [{"message": "no access"}]})).ask("s", QUESTIONS)
    with pytest.raises(ProviderError, match="unexpected"):
        JevClient("a", "t", poster=fake_poster(200, {"result": {"answers": {"ok": {}}}})).ask("s", QUESTIONS)


def test_question_builders_and_settings():
    assert noul("x", true="T", false="F")["criteria"] == {"true": "T", "false": "F"}
    assert score("x", ["a", "b"])["criteria"] == ["a", "b"]
    assert configured({"CLOUDFLARE_ACCOUNT_ID": "a", "CLOUDFLARE_API_TOKEN": "t"})
    assert not configured({"CLOUDFLARE_ACCOUNT_ID": "a"})


def test_cloudflare_double_wrapper_is_unwrapped():
    body = {"state": "Completed", "result": {"model": "jev-1.13.0", "answers": ANSWERS, "usage": {}}}
    assert JevClient("a", "t", poster=fake_poster(200, {"result": body})).ask("s", QUESTIONS) == ANSWERS
