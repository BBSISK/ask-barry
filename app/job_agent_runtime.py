"""Stage 8: the job-ad evidence agent, built on Microsoft Agent Framework.

    client (Azure OpenAI gpt-4.1-mini) + tool (ask_barry over MCP, local mode) + middleware + budget
        -> Agent.run(<job_ad>) -> JSON -> app.job_agent.verify() -> Report

Framework pieces used:
  - Agent / OpenAIChatCompletionClient pointed at the Azure OpenAI v1 endpoint (same deployment as the app)
  - MCPStdioTool launching ask_barry_mcp.py, restricted to the ask_barry tool (allowed_tools)
  - FunctionInvocationConfiguration: hard limits on tool calls, loop iterations and run time
  - function middleware: records every tool call and result (the evidence the report is checked
    against) and refuses anything other than ask_barry
"""
import asyncio
import contextlib
import os
import sys
import time
from pathlib import Path

from app.job_agent import (
    INSTRUCTIONS, blocked_report, content_filter_reason, MAX_TOOL_CALLS, ToolLog, fallback_report, parse_report, user_message, verify,
)

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_TOOL = "ask_barry"
LIMITS = {"max_function_calls": MAX_TOOL_CALLS, "max_iterations": MAX_TOOL_CALLS + 4, "max_duration_seconds": 240}


def result_text(result):
    """Tool results arrive as framework Content objects (or plain values in tests); join their text."""
    items = result if isinstance(result, (list, tuple)) else [result]
    parts = []
    for item in items:
        text = getattr(item, "text", None)
        parts.append(text if isinstance(text, str) else str(item))
    return "".join(parts)


def make_middleware(tool_log, on_call=None):
    """Records every tool call (and refuses any tool but ask_barry). on_call(ToolCall) reports progress."""
    from agent_framework import function_middleware

    def recorded(call):
        if on_call is not None:
            on_call(call)

    @function_middleware
    async def record_tool_calls(context, call_next):
        name = context.function.name
        args = context.arguments.model_dump() if hasattr(context.arguments, "model_dump") else dict(context.arguments)
        if name != ALLOWED_TOOL:                                   # defence in depth; allowed_tools also restricts
            context.result = f"Tool {name!r} is not allowed. Only {ALLOWED_TOOL} may be used."
            recorded(tool_log.record(args.get("question", name), "{}"))
            return
        await call_next()
        recorded(tool_log.record(args.get("question", ""), result_text(context.result)))

    return record_tool_calls


def build_agent(client, tools, tool_log, on_call=None):
    from agent_framework import Agent
    return Agent(client=client, name="job_evidence_agent", instructions=INSTRUCTIONS, tools=tools,
                 middleware=[make_middleware(tool_log, on_call)],
                 default_options={"temperature": 0, "response_format": {"type": "json_object"}})


MODEL_CALL_TIMEOUT = 60        # seconds per model call (the SDK default is 10 minutes, which looks like a freeze)
RUN_TIMEOUT = LIMITS["max_duration_seconds"] + 30     # hard stop for one job ad, whatever hangs


def openai_async_client():
    from openai import AsyncOpenAI

    from app.azure_auth import openai_async_api_key
    from app.embeddings import openai_base_url
    return AsyncOpenAI(api_key=openai_async_api_key(),
                       base_url=openai_base_url(os.environ["AZURE_OPENAI_ENDPOINT"]),
                       timeout=MODEL_CALL_TIMEOUT, max_retries=3)


def azure_client(async_client=None):
    """Agent Framework's OpenAI client on the Azure OpenAI v1 endpoint, with the run limits applied."""
    from agent_framework import FunctionInvocationConfiguration
    from agent_framework_openai import OpenAIChatCompletionClient
    return OpenAIChatCompletionClient(
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], async_client=async_client or openai_async_client(),
        function_invocation_configuration=FunctionInvocationConfiguration(**LIMITS))


def ask_barry_mcp_tool():
    """Your MCP server, launched over stdio in local mode (answers in-process, so no public rate limit)."""
    from agent_framework import MCPStdioTool
    return MCPStdioTool(name="ask_barry_mcp", command=sys.executable, args=[str(ROOT / "ask_barry_mcp.py")],
                        env={**os.environ, "ASK_BARRY_MODE": "local"}, allowed_tools=[ALLOWED_TOOL],
                        approval_mode="never_require", load_prompts=False, request_timeout=90)


async def run(job_ad, client=None, tools=None, on_call=None):
    """Run the agent on one job ad. Returns (Report, stats). Never raises for model misbehaviour.

    on_call(ToolCall) is called after each tool call (the web page uses it to show progress)."""
    message = user_message(job_ad)                    # raises ValueError for empty input
    tool_log = ToolLog()
    tools = tools if tools is not None else [ask_barry_mcp_tool()]
    start = time.time()
    async with contextlib.AsyncExitStack() as stack:
        if client is None:                            # our own HTTP client: closed inside this event loop
            http = openai_async_client()
            stack.push_async_callback(http.close)
            client = azure_client(http)
        for t in tools:                               # MCP tools connect (start the server) on enter
            if hasattr(t, "__aenter__"):
                await stack.enter_async_context(t)
        agent = build_agent(client, tools, tool_log, on_call)
        try:
            response = await asyncio.wait_for(agent.run(message), RUN_TIMEOUT)
            role_title, rows = parse_report(response.text)
            report = verify(role_title, rows, tool_log)
        except ValueError as err:                     # budget hit, or reply wasn't the JSON we asked for
            report = fallback_report(tool_log, str(err)[:80])
        except TimeoutError:                          # something hung: report what the tools returned so far
            report = fallback_report(tool_log, f"stopped after {RUN_TIMEOUT}s")
        except Exception as err:                      # the platform's safety filter refused the ad (layer 0)
            reason = content_filter_reason(err)
            if reason is None:
                raise
            report = blocked_report(reason)
    stats = {"seconds": round(time.time() - start, 1), "tool_calls": len(tool_log.calls),
             "tool_log": [c.__dict__ for c in tool_log.calls]}
    return report, stats
