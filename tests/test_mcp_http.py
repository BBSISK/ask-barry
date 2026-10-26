"""ASK-68: the hosted MCP server at /mcp, tested through the MCP SDK client over real HTTP (offline: fakes behind it)."""
import json
import threading

import urllib.error
import urllib.request

import anyio
import pytest
from mcp import Client
from werkzeug.serving import make_server

from app import create_app
from app.agent_jobs import JobStore
from app.capability.store import CapabilityStore
from app.mcp_http import build_server
from tests.test_answering import StubAnswerer
from tests.test_evidence_web import AD, SyncStore, fake_runner

CAPABILITY = json.loads(open("data/capability.json", encoding="utf-8").read())
TOOLS = {"ask_barry", "get_capability", "match_job_ad"}


def make_app(**kw):
    kw.setdefault("answerer", StubAnswerer())
    kw.setdefault("jobstore", SyncStore(runner=fake_runner))
    kw.setdefault("capability_store", CapabilityStore(source="unused", fetch=lambda _src: CAPABILITY))
    return create_app("testing", **kw)


@pytest.fixture
def live(monkeypatch):
    """The whole WSGI app (Flask + /mcp) on a real local HTTP server, as gunicorn would run it."""
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    app = make_app()
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield app, f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def run(target, fn):
    async def go():
        async with Client(target) as client:
            return await fn(client)
    return anyio.run(go)


def http(method, url, body=None, headers=None):
    """Plain HTTP status code (no MCP client), for the size cap and the routes around /mcp."""
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310 (local test server)
            return resp.status
    except urllib.error.HTTPError as err:
        return err.code


def call(target, name, args):
    return run(target, lambda c: c.call_tool(name, args))


def test_tools_are_listed_read_only_with_structured_output(live):
    _, base = live
    tools = run(f"{base}/mcp", lambda c: c.list_tools()).tools
    assert {t.name for t in tools} == TOOLS
    for tool in tools:
        assert tool.annotations.read_only_hint is True and tool.annotations.destructive_hint is False
        assert tool.output_schema and tool.description


def test_ask_barry_returns_a_cited_answer_marked_ai_generated(live):
    _, base = live
    result = call(f"{base}/mcp", "ask_barry", {"question": "Has Barry used Terraform?"})
    assert not result.is_error
    assert result.structured_content["answer"] == "Barry used Terraform [1]."
    assert result.structured_content["supported"] is True and result.structured_content["ai_generated"] is True


def test_get_capability_one_skill_and_an_unknown_skill(live):
    _, base = live
    skill = CAPABILITY["skills"][0]
    one = call(f"{base}/mcp", "get_capability", {"skill": skill["id"]})
    assert not one.is_error and [s["id"] for s in one.structured_content["skills"]] == [skill["id"]]
    missing = call(f"{base}/mcp", "get_capability", {"skill": "underwater basket weaving"})
    assert missing.is_error and "Skills:" in missing.content[0].text


def test_match_job_ad_returns_the_evidence_map_and_never_echoes_the_ad(live):
    _, base = live
    result = call(f"{base}/mcp", "match_job_ad", {"job_ad": AD})
    assert not result.is_error
    data = result.structured_content
    assert data["status"] == "done" and data["role_title"] == "Platform Engineer"
    assert [(r["requirement"], r["status"]) for r in data["requirements"]] == [
        ("Docker", "evidenced"), ("Kafka", "not_documented")]
    assert data["share_url"].startswith(f"{base}/evidence/shared/")
    assert "jobs@example.com" not in json.dumps(data) and "EUR 50k" not in json.dumps(data)


def test_rate_limits_are_shared_with_the_website_and_429_becomes_is_error(live):
    app, base = live
    web = app.test_client()
    for _ in range(app.config["RATE_LIMIT_PER_MINUTE"]):          # the same visitor uses up the minute on the site
        assert web.post("/api/ask", json={"question": "q"}, environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code == 200
    result = call(f"{base}/mcp", "ask_barry", {"question": "Has Barry used Terraform?"})
    assert result.is_error and "Too many questions" in result.content[0].text


def test_input_caps_are_enforced(live):
    _, base = live
    too_long = call(f"{base}/mcp", "ask_barry", {"question": "x" * 301})
    assert too_long.is_error
    status = http("POST", f"{base}/mcp", b"{" + b" " * 70_000 + b"}",   # bodies past 64 KB are refused
                  {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    assert status == 413


def test_the_website_is_unchanged_behind_the_mount(live):
    _, base = live
    assert http("GET", f"{base}/health") == 200
    assert http("GET", f"{base}/mcp/other") == 404                    # only the exact path is MCP


def test_a_slow_evidence_map_returns_a_link_instead_of_waiting():
    gate = threading.Event()

    def slow_runner(text, on_call):
        gate.wait(5)
        return fake_runner(text, on_call)

    app = make_app(jobstore=JobStore(runner=slow_runner))
    result = call(build_server(app, wait_seconds=0), "match_job_ad", {"job_ad": AD})
    gate.set()
    assert not result.is_error
    assert result.structured_content["status"] == "running" and "/s/" in result.structured_content["share_url"]


def test_a_busy_agent_is_reported_as_an_error_not_a_crash():
    gate = threading.Event()

    def slow_runner(text, on_call):
        gate.wait(5)
        return fake_runner(text, on_call)

    app = make_app(jobstore=JobStore(runner=slow_runner))
    server = build_server(app, wait_seconds=0)
    call(server, "match_job_ad", {"job_ad": AD})
    second = call(server, "match_job_ad", {"job_ad": AD})
    gate.set()
    assert second.is_error and "Another evidence map" in second.content[0].text
