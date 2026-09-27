"""Offline tests for the model providers and the provider comparison (no network)."""
from types import SimpleNamespace

import pytest

from app.answering import Answerer
from app.providers import (
    AnthropicProvider, AzureOpenAIProvider, GeminiProvider, ProviderError, post_with_retries, provider_from_env,
)

MESSAGES = [{"role": "system", "content": "RULES"}, {"role": "user", "content": "Sources...\nQuestion: q"}]
ANSWER_JSON = '{"supported": true, "answer": "Barry used Docker [1].", "citations": [1]}'


def fake_poster(*responses):
    calls = []
    queue = list(responses)

    def poster(url, payload, headers):
        calls.append((url, payload, headers))
        return queue.pop(0) if len(queue) > 1 else queue[0]
    poster.calls = calls
    return poster


# --- Anthropic ----------------------------------------------------------------

def test_anthropic_request_shape_and_parsing():
    poster = fake_poster((200, {"content": [{"type": "text", "text": ANSWER_JSON}],
                                "usage": {"input_tokens": 900, "output_tokens": 40}}))
    p = AnthropicProvider("sk-test", poster=poster)
    assert p.generate(MESSAGES, max_tokens=400) == ANSWER_JSON
    url, payload, headers = poster.calls[0]
    assert url.endswith("/v1/messages") and headers["x-api-key"] == "sk-test" and "anthropic-version" in headers
    assert payload["system"] == "RULES" and payload["messages"] == [MESSAGES[1]]
    assert payload["temperature"] == 0 and payload["max_tokens"] == 400 and payload["model"] == "claude-haiku-4-5"
    assert (p.usage.input_tokens, p.usage.output_tokens) == (900, 40)


def test_anthropic_error_is_raised_with_message():
    p = AnthropicProvider("bad", poster=fake_poster((401, {"error": {"message": "invalid x-api-key"}})))
    with pytest.raises(ProviderError, match="401.*invalid x-api-key"):
        p.generate(MESSAGES)


def test_retries_on_overload_then_succeeds():
    poster = fake_poster((529, {}), (429, {}), (200, {"ok": 1}))
    sleeps = []
    notes = []
    status, body = post_with_retries(poster, "https://api.example/x", {}, {}, sleep=sleeps.append, log=notes.append)
    assert status == 200 and len(poster.calls) == 3 and len(sleeps) == 2
    assert "HTTP 529" in notes[0] and "retrying" in notes[0]            # a wait is announced, never silent


def test_network_timeout_is_retried_then_reported_not_hung():
    import urllib.error

    def poster(url, payload, headers):
        raise urllib.error.URLError("timed out")
    notes = []
    with pytest.raises(ProviderError, match="no response"):
        post_with_retries(poster, "https://g.example/m", {}, {}, attempts=3, sleep=lambda s: None, log=notes.append)
    assert len(notes) == 2


# --- Gemini -------------------------------------------------------------------

def test_gemini_request_shape_skips_thoughts_and_counts_them():
    body = {"candidates": [{"content": {"parts": [{"text": "thinking...", "thought": True}, {"text": ANSWER_JSON}]}}],
            "usageMetadata": {"promptTokenCount": 950, "candidatesTokenCount": 45, "thoughtsTokenCount": 300}}
    poster = fake_poster((200, body))
    p = GeminiProvider("g-key", model="gemini-test", poster=poster)
    assert p.generate(MESSAGES, max_tokens=400) == ANSWER_JSON
    url, payload, headers = poster.calls[0]
    assert url.endswith("/models/gemini-test:generateContent") and headers["x-goog-api-key"] == "g-key"
    assert payload["systemInstruction"]["parts"][0]["text"] == "RULES"
    assert payload["contents"] == [{"role": "user", "parts": [{"text": MESSAGES[1]["content"]}]}]
    cfg = payload["generationConfig"]
    assert cfg["temperature"] == 0 and cfg["responseMimeType"] == "application/json" and cfg["maxOutputTokens"] > 400
    assert p.usage.output_tokens == 345                      # thinking tokens are billed, so they count


def test_gemini_blocked_or_empty_is_an_error():
    p = GeminiProvider("k", poster=fake_poster((200, {"promptFeedback": {"blockReason": "SAFETY"}})))
    with pytest.raises(ProviderError, match="SAFETY"):
        p.generate(MESSAGES)


# --- Azure + wiring -----------------------------------------------------------

def test_azure_provider_keeps_json_mode_and_records_usage():
    calls = []

    def create(**kw):
        calls.append(kw)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=ANSWER_JSON))],
                               usage=SimpleNamespace(prompt_tokens=800, completion_tokens=30))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    p = AzureOpenAIProvider(client, "gpt-4.1-mini")
    assert p.generate(MESSAGES) == ANSWER_JSON
    assert calls[0]["response_format"] == {"type": "json_object"} and calls[0]["temperature"] == 0
    assert p.usage.input_tokens == 800


def test_provider_from_env_defaults_overrides_and_missing_keys():
    assert provider_from_env("anthropic", env={"ANTHROPIC_API_KEY": "k"}).model == "claude-haiku-4-5"
    assert provider_from_env("gemini", env={"GEMINI_API_KEY": "k", "GEMINI_MODEL": "gemini-x"}).model == "gemini-x"
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        provider_from_env("anthropic", env={})
    with pytest.raises(ProviderError, match="unknown provider"):
        provider_from_env("llama", env={})


class FakeProvider:
    name, model = "fake", "fake-1"

    def __init__(self, raw=ANSWER_JSON, fail=False):
        self.raw, self.fail, self.calls = raw, fail, 0
        self.usage = SimpleNamespace(seconds=0.5, input_tokens=100, output_tokens=10)

    def generate(self, messages, max_tokens=400):
        self.calls += 1
        if self.fail:
            raise ProviderError("boom")
        return self.raw


class FakeRetriever:
    def __init__(self):
        self.calls = 0

    def search(self, q, k=8):
        self.calls += 1
        chunk = {"repo": "BBSISK", "path": "README.md", "heading": "Toolbox", "url": "u", "text": "Docker · Terraform"}
        return [SimpleNamespace(chunk=chunk, score=1.0, rank=1)]


def test_answerer_uses_any_provider_and_reports_its_model():
    answer = Answerer(FakeRetriever(), provider=FakeProvider()).ask("Has Barry used Docker?")
    assert answer.supported and answer.model == "fake-1" and answer.answer == "Barry used Docker [1]."


# --- comparison ---------------------------------------------------------------

Q = [{"id": "profile-07", "type": "answerable", "question": "Has Barry used Docker?",
      "expected": ["BBSISK/README.md"], "evidence": ["Docker"]},
     {"id": "trap-01", "type": "trap", "question": "Has Barry used Kubernetes?", "expected": []}]


def judge_ok(kind, *args):
    return {"claims_skill": False, "reason": "no"} if kind == "trap" else {
        "claims": [{"claim": "Docker", "support": "Docker · Terraform"}]}


def test_caching_retriever_gives_every_provider_the_same_sections():
    from scripts.evaluate_answers import CachingRetriever, run_provider
    base = FakeRetriever()
    cached = CachingRetriever(base)
    for provider in (FakeProvider(), FakeProvider()):
        run_provider(Answerer(cached, provider=provider), Q, judge_ok, log=lambda *_: None)
    assert base.calls == 2                                      # once per question, not per provider


def test_provider_failure_becomes_an_error_row_not_a_crash_or_a_pass():
    from scripts.evaluate_answers import run_provider, summarise
    rows, stats = run_provider(Answerer(FakeRetriever(), provider=FakeProvider(fail=True)), Q, judge_ok,
                               log=lambda *_: None)
    assert stats["errors"] == 2 and not any(r["passed"] for r in rows)
    s = summarise(rows)
    assert s["passed"] == 0 and s["trap_no_false_claim"] == 0


def test_comparison_report_lists_providers_and_disagreements():
    from scripts.evaluate_answers import render_comparison, run_provider, summarise
    good = run_provider(Answerer(FakeRetriever(), provider=FakeProvider()), Q, judge_ok, log=lambda *_: None)
    flaky = FakeProvider()
    real_generate = flaky.generate

    def fail_first(messages, max_tokens=400):                   # fails only on the first question
        if flaky.calls == 0:
            flaky.calls += 1
            raise ProviderError("timeout")
        return real_generate(messages, max_tokens)
    flaky.generate = fail_first
    bad = run_provider(Answerer(FakeRetriever(), provider=flaky), Q, judge_ok, log=lambda *_: None)
    report = render_comparison([("a", "m-a", good[0], summarise(good[0]), good[1]),
                                ("b", "m-b", bad[0], summarise(bad[0]), bad[1])], "judge-m", when="2026-09-27")
    assert "| a | `m-a` | 2 of 2 |" in report and "| b | `m-b` | 1 of 2 |" in report
    assert "| profile-07 | ✅ | ❌ |" in report and "Judge: judge-m" in report


def test_judge_runs_on_any_provider():
    from scripts.evaluate_answers import make_judge
    p = FakeProvider(raw='{"claims_skill": false, "reason": "says no"}')
    assert make_judge(p)("trap", "q", "a", "s") == {"claims_skill": False, "reason": "says no"}


def test_provider_is_skipped_after_consecutive_errors():
    from scripts.evaluate_answers import run_provider
    provider = FakeProvider(fail=True)
    many = [dict(Q[0], id=f"p-{i}") for i in range(6)]
    rows, stats = run_provider(Answerer(FakeRetriever(), provider=provider), many, judge_ok, log=lambda *_: None)
    assert provider.calls == 3 and stats["errors"] == 6                  # stopped calling after 3 in a row
    assert all(not r["passed"] for r in rows) and "skipped" in rows[-1]["error"]


def test_unavailable_provider_is_reported_as_not_run_not_as_regressions():
    from scripts.evaluate_answers import render_comparison, run_provider, summarise
    good = run_provider(Answerer(FakeRetriever(), provider=FakeProvider()), Q, judge_ok, log=lambda *_: None)
    dead = run_provider(Answerer(FakeRetriever(), provider=FakeProvider(fail=True)), Q, judge_ok, log=lambda *_: None)
    s_dead = summarise(dead[0])
    assert s_dead["checks_failed"] == 0 and s_dead["errors"] == 2        # errors are not regression failures
    report = render_comparison([("a", "m-a", good[0], summarise(good[0]), good[1]),
                                ("g", "m-g", dead[0], s_dead, dead[1])], "judge-m", when="2026-09-27")
    assert "| g | `m-g` | not run: every call failed |" in report and "first error: ProviderError: boom" in report
    assert "| ID | a |" in report                                         # the dead provider isn't compared
