#!/usr/bin/env node

/**
 * npm wrapper for the ScrapeCrate MCP server.
 * Spawns the Python package via uvx (preferred) or `python3 -m scrapecrate_mcp.server`.
 */

const { spawn } = require("child_process");

function run(command, args) {
  const child = spawn(command, args, {
    stdio: "inherit",
    env: process.env,
  });
  child.on("error", () => {
    console.error(
      "scrapecrate-mcp: could not start the server. Install uv (https://docs.astral.sh/uv/) " +
        "or run `pip install scrapecrate-mcp`."
    );
    process.exit(1);
  });
  child.on("exit", (code) => process.exit(code ?? 1));
  return child;
}

// Try uvx first (fast, no install needed)
const uvx = spawn("uvx", ["scrapecrate-mcp"], {
  stdio: "inherit",
  env: process.env,
});

uvx.on("error", () => {
  // uvx not available, fall back to python3 -m
  run("python3", ["-m", "scrapecrate_mcp.server"]);
});

uvx.on("exit", (code) => {
  if (code !== null) process.exit(code);
});
