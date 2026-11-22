# Runs the ScrapeCrate MCP server over stdio (registries' automated checks, container use).
# Usage: docker run -i --rm -e SCRAPECRATE_API_KEY=... scrapecrate-mcp
# The hosted server (no install, OAuth sign-in) is https://api.scrapecrate.com/mcp.
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
ENTRYPOINT ["scrapecrate-mcp"]
