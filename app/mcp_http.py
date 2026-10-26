"""ASK-68: Ask Barry as a hosted MCP server at /mcp, so anyone can add it to an AI assistant by URL.

Streamable HTTP transport (MCP Python SDK 2.x), stateless and JSON-only: every POST is one complete request and
one complete response, with no session to keep. That fits a single small web instance, and it is why the server
can sit inside the existing Flask app instead of needing its own process.

Read-only and public, like the website. No login, because the data is the public GitHub docs.

How it fits together:
  - McpMount sits in front of Flask. Requests for /mcp go to the SDK's ASGI app, through a2wsgi, on one
    long-lived event loop thread; everything else goes to Flask unchanged.
  - Each tool calls the app's own JSON API in-process (/api/ask, /api/capability, /api/evidence) with the
    caller's IP. So the MCP tools get exactly the website's validation, rate limits, size caps, privacy rules
    (questions and ads are not logged or stored) and AI disclosure. There is no second copy of any of it.
"""
import asyncio
import threading
import time
from typing import Optional

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from ask_barry_mcp import INSTRUCTIONS, AskBarryResult, CapabilityResult, CitedSource, to_capability_result

from .job_agent import MAX_JOB_AD_CHARS

PATH = "/mcp"
MAX_BODY_BYTES = 64 * 1024        # the longest legitimate call is an 8,000-character job ad
POLL_SECONDS = 2
WAIT_SECONDS = 150                # an evidence map takes 30-60 s; after this, hand back a link instead of waiting
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

HOSTED_INSTRUCTIONS = INSTRUCTIONS + (
    " match_job_ad maps a pasted job ad to evidence, requirement by requirement. It reports evidence, never a "
    "verdict on fit, and it is limited to a few runs an hour."
)


class RequirementEvidence(BaseModel):
    requirement: str
    kind: str = Field(description="must or nice (as the ad presents it)")
    status: str = Field(description="evidenced, listed_on_profile, related_only or not_documented")
    evidence: str = Field("", description="What the docs show, checked against the tool answers")
    sources: list[str] = Field(default_factory=list, description="GitHub links to the evidence")


class JobAdMatchResult(BaseModel):
    status: str = Field(description="done, or running if it took too long to wait for (then open share_url later)")
    role_title: str = ""
    requirements: list[RequirementEvidence] = Field(default_factory=list)
    dropped: list[str] = Field(default_factory=list, description="Requirements past the row limit, not checked")
    markdown: str = Field("", description="The evidence map as a readable table")
    share_url: str = Field("", description="Signed link to this evidence map on the Ask Barry website")
    ai_generated: bool = True
    note: str = ("Evidence in Barry's public project docs, requirement by requirement. Not a score or a verdict "
                 "on fit: 'not_documented' means the docs don't show it, not that the skill is missing.")


def _caller(ctx):
    """(client IP, public base URL) of the HTTP request behind this tool call."""
    request = getattr(ctx.request_context, "request", None)
    if request is None:                         # in-memory client (tests): no HTTP request
        return "unknown", "http://localhost"
    ip = request.client.host if request.client else "unknown"
    return ip, f"{request.url.scheme}://{request.headers.get('host', 'localhost')}"


def _error(resp):
    body = resp.get_json(silent=True) or {}
    return body.get("error") or f"Ask Barry returned HTTP {resp.status_code}."


def build_server(flask_app, wait_seconds=WAIT_SECONDS, poll_seconds=POLL_SECONDS, sleep=time.sleep):
    """The hosted MCP server. Its tools call flask_app's own JSON API in-process."""
    server = MCPServer("Ask Barry", instructions=HOSTED_INSTRUCTIONS)

    def call(ctx, method, path, **kw):
        ip, base = _caller(ctx)
        client = flask_app.test_client()          # an in-process WSGI call, not a network request
        return getattr(client, method)(path, base_url=base, environ_base={"REMOTE_ADDR": ip}, **kw)

    @server.tool(name="ask_barry", title="Ask about Barry Sisk's projects", annotations=READ_ONLY)
    def ask_barry(
        ctx: Context,
        question: str = Field(description="A question about Barry's projects, skills or experience "
                                          "(max 300 characters)", max_length=300),
    ) -> AskBarryResult:
        """Ask a question about Barry Sisk's software projects, skills or experience.

        Answers come only from his public GitHub documentation, each with cited sources (repo, file,
        section and link). Returns supported=false when the documentation doesn't evidence the claim.
        """
        resp = call(ctx, "post", "/api/ask", json={"question": question})
        if resp.status_code != 200:
            raise ToolError(_error(resp))
        body = resp.get_json()
        return AskBarryResult(
            answer=body["answer"], supported=bool(body["supported"]), model=body.get("model", ""),
            sources=[CitedSource(**{k: s[k] for k in ("number", "repo", "path", "heading", "url")})
                     for s in body.get("sources") or []],
            ai_generated=True)

    @server.tool(name="get_capability", title="Barry Sisk's capability ladder", annotations=READ_ONLY)
    def get_capability(
        ctx: Context,
        skill: Optional[str] = Field(None, description="Optional skill id or name, e.g. 'containers'. "
                                                       "Leave empty for every skill.", max_length=80),
    ) -> CapabilityResult:
        """How far each skill goes in Barry's public projects, tier by tier (e.g. Used, Built, In production,
        Tested / evaluated), with links and quotes for the evidence. Gaps are included as tier 0. Rebuilt nightly.
        """
        resp = call(ctx, "get", "/api/capability", query_string={"skill": skill} if skill else None)
        if resp.status_code == 404:
            body = resp.get_json()
            raise ToolError(f"{body['error']} Skills: {', '.join(body.get('skills', []))}")
        if resp.status_code != 200:
            raise ToolError(_error(resp))
        return to_capability_result(resp.get_json())

    @server.tool(name="match_job_ad", title="Map a job ad to Barry's evidence",
                 annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=False,
                                             open_world_hint=False))
    def match_job_ad(
        ctx: Context,
        job_ad: str = Field(description=f"The job advertisement text (max {MAX_JOB_AD_CHARS} characters). "
                                        "It is not stored or logged.", max_length=MAX_JOB_AD_CHARS),
    ) -> JobAdMatchResult:
        """Map each requirement in a job ad to evidence in Barry's public project docs, with links.

        Runs the same guarded agent as the Ask Barry website's /evidence page: it reports what the docs show
        for each requirement and never scores or judges fit. Takes 30-60 seconds; limited to a few runs an hour.
        """
        resp = call(ctx, "post", "/api/evidence", json={"job_ad": job_ad})
        if resp.status_code != 202:
            raise ToolError(_error(resp))
        job_id = resp.get_json()["id"]
        deadline = time.monotonic() + wait_seconds
        while True:
            job = call(ctx, "get", f"/api/evidence/{job_id}").get_json()
            if job.get("status") != "running" or time.monotonic() >= deadline:
                break
            sleep(poll_seconds)
        if job.get("status") not in ("done", "running"):         # "error", or the job expired (404)
            raise ToolError(job.get("error") or "Sorry, something went wrong preparing the evidence map.")
        _, base = _caller(ctx)
        if job["status"] == "running":
            return JobAdMatchResult(status="running", share_url=f"{base}/s/{job_id}")
        report = job["report"] or {}
        if report.get("blocked"):
            raise ToolError(report["blocked"])
        return JobAdMatchResult(
            status="done", role_title=report.get("role_title", ""), dropped=report.get("dropped") or [],
            requirements=[RequirementEvidence(**{k: r.get(k) for k in ("requirement", "kind", "status", "evidence",
                                                                        "sources") if r.get(k) is not None})
                          for r in report.get("requirements") or []],
            markdown=job.get("markdown", ""), share_url=(job.get("share") or {}).get("url", ""))

    return server


class McpMount:
    """WSGI middleware: /mcp goes to the MCP server's ASGI app, everything else to the wrapped Flask app.

    The SDK's session manager must run inside a long-lived task group (its "lifespan"), so one background
    thread owns one event loop for the life of the process. It starts on the first /mcp request, so the
    website itself never pays for it.
    """

    def __init__(self, wsgi_app, server):
        self.wsgi_app = wsgi_app
        self.server = server
        self._asgi = None
        self._lock = threading.Lock()

    def _start(self):
        from a2wsgi import ASGIMiddleware
        asgi = self.server.streamable_http_app(
            streamable_http_path=PATH, stateless_http=True, json_response=True,
            max_request_body_size=MAX_BODY_BYTES,
            # DNS-rebinding protection guards servers on a user's own machine. This one is public, read-only
            # and has no login, so a rebinding page could learn nothing it couldn't fetch directly.
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))
        loop = asyncio.new_event_loop()
        ready = threading.Event()

        async def lifespan():
            async with asgi.router.lifespan_context(asgi):
                ready.set()
                await asyncio.Event().wait()          # held open for the life of the process

        def run():
            asyncio.set_event_loop(loop)
            loop.run_until_complete(lifespan())

        threading.Thread(target=run, name="mcp-loop", daemon=True).start()
        if not ready.wait(10):
            raise RuntimeError("The MCP session manager did not start.")
        return ASGIMiddleware(asgi, loop=loop)

    def __call__(self, environ, start_response):
        if environ.get("PATH_INFO", "") != PATH:
            return self.wsgi_app(environ, start_response)
        with self._lock:
            if self._asgi is None:
                self._asgi = self._start()
        return self._asgi(environ, start_response)
