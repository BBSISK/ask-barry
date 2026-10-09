"""Offline tests for the Ask Barry MCP server (no network: the HTTP call is faked)."""
import json

import anyio
import pytest

import ask_barry_mcp as server
from ask_barry_mcp import AskBarryError, ask

LIVE_BODY = {
    "question": "q", "answer": "Barry used Docker [1].", "supported": True, "retrieved": 8,
    "model": "gpt-4.1-mini", "ai_generated": True,
    "sources": [{"number": 1, "repo": "BBSISK", "path": "README.md", "heading": "Toolbox",
                 "url": "https://github.com/BBSISK/BBSISK/blob/abc/README.md#toolbox"}],
}


def fake_poster(status=200, body=None, error=None):
    calls = []

    def poster(url, payload):
        calls.append((url, payload))
        if error:
            raise error
        return status, body if body is not None else LIVE_BODY
    poster.calls = calls
    return poster


def test_ask_calls_the_live_api_and_keeps_citations():
    poster = fake_poster()
    result = ask("  Has Barry   used Docker? ", base_url="https://example.test/", poster=poster)
    assert poster.calls == [("https://example.test/api/ask", {"question": "Has Barry used Docker?"})]
    assert result.supported and result.answer == "Barry used Docker [1]."
    assert result.sources[0].url.endswith("#toolbox") and result.ai_generated


def test_unsupported_answer_is_passed_through_not_an_error():
    body = {**LIVE_BODY, "supported": False, "sources": [],
            "answer": "I can't find evidence of that in Barry's public GitHub documentation."}
    result = ask("Has Barry used X?", poster=fake_poster(body=body))
    assert result.supported is False and result.sources == []


@pytest.mark.parametrize("status,body,expected", [
    (429, {"error": "Too many questions in a minute."}, "Rate limited"),
    (400, {"error": "Please keep questions under 300 characters."}, "HTTP 400"),
    (503, {"error": "Answering is not configured on this server."}, "HTTP 503"),
])
def test_http_errors_become_readable_messages(status, body, expected):
    with pytest.raises(AskBarryError, match=expected):
        ask("q", poster=fake_poster(status=status, body=body))


def test_network_failure_suggests_cold_start():
    with pytest.raises(AskBarryError, match="waking up"):
        ask("q", poster=fake_poster(error=TimeoutError("timed out")))


def test_empty_question_is_rejected_without_calling_the_api():
    poster = fake_poster()
    with pytest.raises(AskBarryError):
        ask("   ", poster=poster)
    assert poster.calls == []


def test_default_url_and_env_override(monkeypatch):
    poster = fake_poster()
    ask("q", poster=poster)
    assert poster.calls[-1][0] == "https://ask-barry.onrender.com/api/ask"
    monkeypatch.setenv("ASK_BARRY_URL", "http://127.0.0.1:5000")
    ask("q", poster=poster)
    assert poster.calls[-1][0] == "http://127.0.0.1:5000/api/ask"


# --- over the real MCP protocol (in-memory client <-> server) --------------------

def run_client(fn):
    from mcp.shared.memory import create_connected_server_and_client_session

    async def main():
        async with create_connected_server_and_client_session(server.mcp._mcp_server) as client:
            return await fn(client)
    return anyio.run(main)


def test_tool_is_listed_read_only_with_schemas():
    tools = run_client(lambda c: c.list_tools()).tools
    assert [t.name for t in tools] == ["ask_barry", "get_capability"]
    assert all(t.annotations.readOnlyHint is True for t in tools)
    tool = tools[0]
    assert tool.annotations.readOnlyHint is True and tool.annotations.destructiveHint is False
    assert tool.inputSchema["required"] == ["question"]
    assert tool.inputSchema["properties"]["question"]["maxLength"] == 300
    assert {"answer", "supported", "sources"} <= set(tool.outputSchema["properties"])


def test_tool_call_returns_structured_answer(monkeypatch):
    monkeypatch.setattr(server, "post_json", fake_poster())
    result = run_client(lambda c: c.call_tool("ask_barry", {"question": "Has Barry used Docker?"}))
    assert result.isError is False
    assert result.structuredContent["supported"] is True
    assert result.structuredContent["sources"][0]["repo"] == "BBSISK"
    assert "Barry used Docker" in result.content[0].text


def test_tool_call_reports_rate_limit_as_tool_error(monkeypatch):
    monkeypatch.setattr(server, "post_json", fake_poster(status=429, body={"error": "slow down"}))
    result = run_client(lambda c: c.call_tool("ask_barry", {"question": "q"}))
    assert result.isError is True and "Rate limited" in result.content[0].text


def test_check_mode_prints_json(capsys, monkeypatch):
    monkeypatch.setattr(server, "post_json", fake_poster())
    server.main(["--check", "What is Wall Inspector?"])
    assert json.loads(capsys.readouterr().out)["supported"] is True


# --- ASK-42: get_capability reads the same capability.json as the page -----------------------------------------

CAP = {"schema_version": "1.0", "profile_id": "p", "person": {"name": "Barry Sisk", "short_name": "Barry"},
       "generated_at": "2026-10-09T03:30:00Z", "sources": {"repos": ["wall_inspector"]},
       "tiers": [{"level": n, "universal": u, "label": l} for n, u, l in
                 [(1, "Learned", "Used"), (2, "Applied", "Built"), (3, "Delivered", "In production"),
                  (4, "Proven", "Tested / evaluated")]],
       "skills": [{"id": "containers", "name": "Containers (Docker)", "tier": 3, "first_evidence": "2025-11",
                   "projects_by_tier": {"3": ["Wall Inspector"]},
                   "evidence": [{"tier": 3, "repo": "wall_inspector", "path": "README.md", "heading": "Deployment",
                                 "url": "https://github.com/BBSISK/wall_inspector/blob/abc/README.md#d",
                                 "quote": "Render auto-deploys the Docker container", "source_type": "github_readme",
                                 "verified_by": "self", "project": "Wall Inspector"}]},
                  {"id": "java", "name": "Java", "tier": 0, "first_evidence": None, "projects_by_tier": {},
                   "evidence": []}],
       "cards": []}


def fake_getter(status=200, body=None):
    calls = []

    def getter(url, timeout=None):
        calls.append(url)
        return status, CAP if body is None else body
    getter.calls = calls
    return getter


def test_capability_calls_the_api_and_labels_tiers():
    getter = fake_getter()
    result = server.capability(getter=getter)
    assert getter.calls == ["https://ask-barry.onrender.com/api/capability"]
    assert [(s.id, s.tier_label) for s in result.skills] == [("containers", "In production"), ("java", "Not evidenced")]
    assert result.skills[0].projects == ["Wall Inspector"] and result.evidence_as_of == "2026-10-09"
    server.capability("Containers (Docker)", getter=getter)
    assert getter.calls[-1].endswith("/api/capability?skill=Containers%20%28Docker%29")


def test_capability_unknown_skill_lists_the_skills():
    with pytest.raises(server.AskBarryError, match="Skills: containers, java"):
        server.capability("juggling", getter=fake_getter(404, {"error": "No skill 'juggling'.", "skills": ["containers", "java"]}))


def test_get_capability_over_the_protocol(monkeypatch):
    monkeypatch.setattr(server, "get_json", fake_getter())
    result = run_client(lambda c: c.call_tool("get_capability", {}))
    assert result.isError is False
    assert result.structuredContent["skills"][0]["tier_label"] == "In production"
    assert "not a self-rating" in result.structuredContent["note"]
