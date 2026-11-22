"""Build MCP tool definitions from the public catalog, and run a tool call."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any
from urllib.parse import quote

import httpx

MAX_TEXT = 60_000  # keep tool results within what assistants handle well

_JSON_TYPES = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "date": "string",
}


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    path: str
    path_params: list[str]
    is_list: bool


def bundled_catalog() -> dict:
    return json.loads(resources.files("scrapecrate_mcp").joinpath("catalog.json").read_text("utf-8"))


async def load_catalog(base_url: str, timeout: float = 5.0) -> dict:
    """Live catalog (new APIs appear without a release), bundled copy as a fallback."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.get(f"{base_url}/v1/catalog")
            if r.status_code == 200:
                body = r.json()
                if isinstance(body, dict) and body.get("apis"):
                    return body
    except (httpx.HTTPError, ValueError):
        pass
    return bundled_catalog()


def _price(p: dict) -> str:
    c = p["credits"]
    unit = "credit" if c == 1 else "credits"
    if p["unit"] == "call":
        return f"{c} {unit} per call"
    text = f"{c} {unit} per {p.get('per', 1)} items returned (min {p.get('min') or c})"
    nested = p.get("nested")
    if nested:
        text += (
            f"; with {nested['when']}=true the nested items (up to {nested['max_param']} per"
            " item) count as items too"
        )
    return text


def _schema(param: dict) -> dict:
    t = param.get("type", "string")
    s: dict[str, Any] = (
        {"type": "string", "enum": param["values"]} if t == "enum" else {"type": _JSON_TYPES[t]}
    )
    if t == "date":
        s["format"] = "date"
    for src, dst in (("min", "minimum"), ("max", "maximum"), ("default", "default")):
        if param.get(src) is not None:
            s[dst] = param[src]
    if param.get("description"):
        s["description"] = param["description"]
    return s


def build_tools(catalog: dict) -> list[Tool]:
    tools: list[Tool] = []
    for api in catalog["apis"]:
        for ep in api["endpoints"]:
            params = ep.get("params", [])
            props = {p["name"]: _schema(p) for p in params}
            required = [p["name"] for p in params if p.get("required") or p.get("in") == "path"]
            description = f"{api['name']}: {ep['summary']}. {ep.get('description', '')}".strip()
            description += f" Price: {_price(ep['pricing'])}; failed calls are free."
            if ep.get("list"):
                description += (
                    " Paginated: pass pagination.next_cursor as `cursor` for the next page"
                    " (each page is a new call)."
                )
            if ep.get("require_one_of"):
                description += f" One of {', '.join(ep['require_one_of'])} is required."
            tools.append(
                Tool(
                    name=f"{api['id']}_{ep['id'].replace('-', '_')}",
                    description=description,
                    input_schema={"type": "object", "properties": props, "required": required},
                    path=ep.get("path") or f"/v1/{api['id']}",
                    path_params=[p["name"] for p in params if p.get("in") == "path"],
                    is_list=bool(ep.get("list")),
                )
            )
    tools.append(
        Tool(
            name="account_balance",
            description="Your remaining credits (free monthly and purchased). Free of charge.",
            input_schema={"type": "object", "properties": {}},
            path="/v1/account",
            path_params=[],
            is_list=False,
        )
    )
    return tools


async def call_tool(tool: Tool, args: dict[str, Any], client: httpx.AsyncClient) -> tuple[bool, str]:
    """Returns (is_error, text)."""
    path = tool.path
    query: dict[str, str] = {}
    for k, v in (args or {}).items():
        if v is None or v == "":
            continue
        if k in tool.path_params:
            path = path.replace("{" + k + "}", quote(str(v), safe=""))
        else:
            query[k] = ("true" if v else "false") if isinstance(v, bool) else str(v)
    missing = [p for p in tool.path_params if "{" + p + "}" in path]
    if missing:
        return True, f"Missing required argument(s): {', '.join(missing)}"
    try:
        r = await client.get(path, params=query)
    except httpx.HTTPError as e:
        return True, f"Could not reach the API: {type(e).__name__}"
    try:
        body = r.json()
    except ValueError:
        return True, f"HTTP {r.status_code}"
    if r.status_code != 200:
        err = body.get("error", {}) if isinstance(body, dict) else {}
        text = f"Error {r.status_code} {err.get('code', '')}: {err.get('message', '')}"
        if err.get("details"):
            text += f"\nDetails: {json.dumps(err['details'])}"
        return True, text
    text = json.dumps(body, ensure_ascii=False, indent=1)
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT] + "\n… (truncated: use a smaller `limit`)"
    return False, text
