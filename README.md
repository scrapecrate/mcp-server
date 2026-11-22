# ScrapeCrate MCP server

<!-- mcp-name: com.scrapecrate/scrapecrate -->

Gives Claude, Cursor, Windsurf and any MCP client every ScrapeCrate endpoint as a tool:
YouTube (transcripts, metadata, comments, channels, search), Google Maps (places, details,
reviews), Trustpilot (companies, reviews), App Store and Google Play (apps, reviews) and the Meta
Ad Library (ads, advertisers).
One tool per endpoint, built from the live catalog, plus `account_balance`.

## Hosted server (no install, no key)

Add `https://api.scrapecrate.com/mcp` as a remote MCP server (Streamable HTTP) and sign in with your
ScrapeCrate account when the client asks: Claude (Settings → Connectors → Add custom connector),
ChatGPT (developer mode connector, OAuth), or Claude Code:

```bash
claude mcp add --transport http scrapecrate https://api.scrapecrate.com/mcp
```

Same tools and prices as the local server below, billed to the signed-in account.

## Local server (API key)

Create an API key at https://scrapecrate.com/dashboard/api-keys, then add to your client:

```json
{
  "mcpServers": {
    "scrapecrate": {
      "command": "uvx",
      "args": ["scrapecrate-mcp"],
      "env": { "SCRAPECRATE_API_KEY": "YOUR_API_KEY" }
    }
  }
}
```

Claude Code: `claude mcp add scrapecrate -e SCRAPECRATE_API_KEY=YOUR_API_KEY -- uvx scrapecrate-mcp`

Tool calls cost the same credits as API calls; failed calls are free.
Docs: https://scrapecrate.com/docs/mcp

## Development

```bash
uv venv && uv pip install -e ".[dev]" && pytest
SCRAPECRATE_BASE_URL=http://localhost:8070 SCRAPECRATE_API_KEY=... scrapecrate-mcp
```
