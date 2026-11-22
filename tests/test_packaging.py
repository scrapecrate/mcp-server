"""Directory metadata (official MCP registry, Glama) stays consistent with the package."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = (ROOT / "pyproject.toml").read_text("utf-8")  # no tomllib: Python 3.10 is supported


def _field(name: str) -> str:
    return re.search(rf'^{name} = "([^"]+)"', PYPROJECT, re.M).group(1)


def test_server_json_matches_the_package():
    server = json.loads((ROOT / "server.json").read_text("utf-8"))
    readme = (ROOT / "README.md").read_text("utf-8")

    assert server["name"].startswith("com.scrapecrate/")
    # PyPI ownership proof: the README of the published version carries the registry name
    assert f"<!-- mcp-name: {server['name']} -->" in readme
    (package,) = server["packages"]
    assert package["registryType"] == "pypi"
    assert package["identifier"] == _field("name")
    assert package["version"] == _field("version") == server["version"]
    assert package["transport"] == {"type": "stdio"}
    assert [v["name"] for v in package["environmentVariables"]] == ["SCRAPECRATE_API_KEY"]
    assert server["remotes"] == [{"type": "streamable-http", "url": "https://api.scrapecrate.com/mcp"}]
    assert len(server["description"]) <= 100


def test_glama_and_dockerfile():
    glama = json.loads((ROOT / "glama.json").read_text("utf-8"))
    assert glama["maintainers"]
    dockerfile = (ROOT / "Dockerfile").read_text("utf-8")
    assert re.search(r'ENTRYPOINT \["scrapecrate-mcp"\]', dockerfile)
    assert 'scrapecrate-mcp = "scrapecrate_mcp.server:main"' in PYPROJECT
