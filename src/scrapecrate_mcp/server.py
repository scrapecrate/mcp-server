"""stdio MCP server. Env: SCRAPECRATE_API_KEY (required), SCRAPECRATE_BASE_URL (optional)."""

from __future__ import annotations

import asyncio
import os
import sys

import httpx
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from . import __version__
from .tools import Tool, build_tools, call_tool, load_catalog

DEFAULT_BASE_URL = "https://api.scrapecrate.com"


def create_server(tools: list[Tool], client: httpx.AsyncClient) -> Server:
    server: Server = Server("scrapecrate", version=__version__)
    by_name = {t.name: t for t in tools}

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [types.Tool(name=t.name, description=t.description, inputSchema=t.input_schema) for t in tools]

    @server.call_tool()
    async def handle(name: str, arguments: dict | None) -> list[types.TextContent]:
        tool = by_name.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        is_error, text = await call_tool(tool, arguments or {}, client)
        if is_error:
            raise ValueError(text)
        return [types.TextContent(type="text", text=text)]

    return server


async def run() -> None:
    api_key = os.environ.get("SCRAPECRATE_API_KEY")
    if not api_key:
        print("SCRAPECRATE_API_KEY is not set: create a key in the dashboard.", file=sys.stderr)
        sys.exit(1)
    base_url = os.environ.get("SCRAPECRATE_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    catalog = await load_catalog(base_url)
    tools = build_tools(catalog)
    headers = {"X-API-Key": api_key, "User-Agent": f"scrapecrate-mcp/{__version__}"}
    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=120) as client:
        server = create_server(tools, client)
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
