"""ASK-66: the job-ad agent talks to ask_barry_mcp.py as a real subprocess over stdio, through Microsoft Agent
Framework's MCPStdioTool. Unit tests with in-memory clients can't see a missing runtime dependency or an SDK
mismatch between the two packages, so this test starts the server exactly as the live agent does (offline: listing
tools needs no network or Azure)."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agent_framework_reaches_the_mcp_server_over_stdio():
    from agent_framework import MCPStdioTool

    async def main():
        tool = MCPStdioTool(name="ask_barry_mcp", command=sys.executable, args=[str(ROOT / "ask_barry_mcp.py")],
                            allowed_tools=["ask_barry"])
        async with tool:
            return [f.name for f in tool.functions]

    assert asyncio.run(asyncio.wait_for(main(), timeout=60)) == ["ask_barry"]


def test_sdk_client_reaches_the_mcp_server_over_stdio():
    import anyio
    from mcp import Client, StdioServerParameters

    async def main():
        params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "ask_barry_mcp.py")])
        async with Client(params) as client:
            return [t.name for t in (await client.list_tools()).tools]

    assert anyio.run(main) == ["ask_barry", "get_capability"]
