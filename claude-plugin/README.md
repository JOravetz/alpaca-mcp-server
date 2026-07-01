# alpaca-trading plugin

Claude Code plugin bundling the enhanced Alpaca MCP server (this repo) with the
day-trading scanner slash commands, so the whole trading setup installs as one unit.

## What it provides

- **MCP server `alpaca-trading`** — launched via `uv` from this repo
  (`python -m alpaca_mcp_server`): ~120 tools for scanners, streaming
  quotes/bars, peak/trough analysis, support/resistance, order placement,
  price triggers, and position monitoring.
- **`/alpaca-trading:scan`** — quick explosive stock scan (trades/min +
  percent-change thresholds).
- **`/alpaca-trading:gaps`** — pre-market gap and extended-hours mover scanner.
- **`/alpaca-trading:morning_scanner`** — full scanner suite for the market open.

## Requirements

- `uv` at `~/.local/bin/uv` and this repo checked out at
  `~/alpaca-mcp-server-enhanced` (the MCP config points there by absolute path).
- `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` set in the OS environment.
  No credentials are stored in the plugin — the config expands them at launch.
- `ALPACA_BASE_URL` defaults to the paper-trading endpoint; edit
  `.claude-plugin/plugin.json` to point at the live API.

## Install

The repo root doubles as a local plugin marketplace:

```
/plugin marketplace add /home/jjoravet/alpaca-mcp-server-enhanced
/plugin install alpaca-trading@alpaca-local
```

## After installing

Avoid loading the server twice:

- Remove the `alpaca-trading` entry from `~/.mcp.json` (the plugin now owns it).
- Optionally delete `~/.claude/commands/{scan,gaps,morning_scanner}.md` — the
  plugin registers the same commands under the `alpaca-trading:` prefix.
