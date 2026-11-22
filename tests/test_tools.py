from __future__ import annotations

import json

import httpx
import pytest

from scrapecrate_mcp.server import create_server
from scrapecrate_mcp.tools import build_tools, bundled_catalog, call_tool, load_catalog


def test_one_tool_per_endpoint_plus_balance():
    cat = bundled_catalog()
    tools = build_tools(cat)
    n = sum(len(a["endpoints"]) for a in cat["apis"])
    assert len(tools) == n + 1
    names = {t.name for t in tools}
    assert {
        "youtube_transcript",
        "maps_place_reviews",
        "trustpilot_company_reviews",
        "ads_ads_search",
        "account_balance",
    } <= names


def test_schemas():
    tools = {t.name: t for t in build_tools(bundled_catalog())}
    s = tools["maps_places_search"].input_schema
    assert s["required"] == ["q"]
    assert s["properties"]["limit"]["maximum"] == 20
    assert "Price: 3 credits per call" in tools["maps_places_search"].description
    assert "each page is a new call" in tools["maps_places_search"].description
    assert "Price: 1 credit per 100 items returned (min 1)" in tools["youtube_video_comments"].description
    assert "Price: 8 credits per call" in tools["trustpilot_company"].description
    assert tools["youtube_transcript"].input_schema["properties"]["format"]["enum"] == ["json", "text", "srt"]


def test_no_private_names():
    text = json.dumps(bundled_catalog()).lower()
    for w in ("upstream", "legacy", "satellite", "fetch" "transcript", "internal/v1", "env_prefix"):
        assert w not in text


def _client(handler):
    return httpx.AsyncClient(base_url="https://api.test", transport=httpx.MockTransport(handler))


async def test_call_success_and_path_escaping():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"data": {"ok": True}, "meta": {"credits_used": 2}})

    tools = {t.name: t for t in build_tools(bundled_catalog())}
    async with _client(handler) as c:
        is_err, text = await call_tool(
            tools["trustpilot_company"], {"domain": "a.com", "include_similar": True}, c
        )
    assert not is_err and '"ok": true' in text
    assert seen["url"] == "https://api.test/v1/trustpilot/companies/a.com?include_similar=true"


async def test_call_error_and_missing_args():
    tools = {t.name: t for t in build_tools(bundled_catalog())}
    async with _client(
        lambda r: httpx.Response(402, json={"error": {"code": "insufficient_credits", "message": "Top up"}})
    ) as c:
        is_err, text = await call_tool(tools["maps_place"], {"place_id": "x"}, c)
        assert is_err and "insufficient_credits" in text
        is_err, text = await call_tool(tools["maps_place"], {}, c)
        assert is_err and "place_id" in text


async def test_live_catalog_fallback():
    cat = await load_catalog("http://127.0.0.1:9", timeout=0.2)
    assert cat["apis"]


async def test_server_lists_and_calls_tools():
    import mcp.types as types

    tools = build_tools(bundled_catalog())
    async with _client(lambda r: httpx.Response(200, json={"data": [1], "meta": {}})) as c:
        server = create_server(tools, c)
        listed = await server.request_handlers[types.ListToolsRequest](
            types.ListToolsRequest(method="tools/list")
        )
        assert len(listed.root.tools) == len(tools)
        res = await server.request_handlers[types.CallToolRequest](
            types.CallToolRequest(
                method="tools/call",
                params=types.CallToolRequestParams(name="youtube_search", arguments={"q": "x"}),
            )
        )
        assert not res.root.isError and '"data"' in res.root.content[0].text


@pytest.mark.parametrize("name", ["nope"])
async def test_unknown_tool_is_error(name):
    import mcp.types as types

    async with _client(lambda r: httpx.Response(200, json={})) as c:
        server = create_server(build_tools(bundled_catalog()), c)
        res = await server.request_handlers[types.CallToolRequest](
            types.CallToolRequest(
                method="tools/call", params=types.CallToolRequestParams(name=name, arguments={})
            )
        )
        assert res.root.isError
