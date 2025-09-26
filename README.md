# MCP TradingView Server

FastMCP v2 server that exposes TradingView technical indicators and OHLCV data through the `tradingview_scraper` library. The `mcp-tradingview` console entry powers Claude Desktop or any MCP-aware client.

## Quick Start

### Automated Setup (Recommended)

1. Install [uv](https://astral.sh/uv) and Python 3.11+
2. Run the setup script: `./setup.sh`
   - Installs dependencies and creates virtual environment
   - Automatically configures Claude Desktop with the MCP server
3. Restart Claude Desktop to load the new configuration

### Manual Setup

1. Install [uv](https://astral.sh/uv) and Python 3.11+
2. `uv venv --python 3.11 && source .venv/bin/activate`
3. `uv pip install -e .`
4. Configure Claude Desktop (see below)

## Running

- Stdio (Claude default): `uv run mcp-tradingview`
- SSE service: `uv run mcp-tradingview --transport sse --host 0.0.0.0 --port 8000`
- HTTP service: `uv run mcp-tradingview --transport http --host 0.0.0.0 --port 8000 --path /mcp`

`FASTMCP_HOST`, `FASTMCP_PORT`, and `FASTMCP_PATH` environment variables override the bind settings when present.

## Tools

- `get_indicators(symbol, exchange="BINANCE", timeframe="1h", all_indicators=True, export_result=False)` – full TradingView indicator snapshot; returns `success`, `symbol`, `exchange`, `timeframe`, and an `indicators` mapping.
- `get_specific_indicators(symbol, indicators, exchange="BINANCE", timeframe="1h", export_result=False)` – filters the full snapshot to requested keys (case-insensitive) and echoes `requested_indicators`.
- `get_historical_data(symbol, exchange="BINANCE", timeframe="1h", max_records=100, export_result=False)` – streams OHLCV candles via `Streamer`, returning `records_collected`, `data`, and optional `export_file`.

## Resources & Exports

- Resource `indicators/{symbol}` emits a formatted indicator report using `get_indicators` defaults.
- When `export_result=True`, JSON payloads are written to `export/`; keep large archives out of version control.

## Claude Desktop

Add the server to `claude_desktop_config.json`. Here are the recommended configurations:

### Using Claude Code CLI (Easiest)

```bash
claude mcp add tradingview -- uvx --from /absolute/path/to/mcp-tradingview-server mcp-tradingview
```

Or with uv run:

```bash
claude mcp add tradingview -- uv run mcp-tradingview --cwd /absolute/path/to/mcp-tradingview-server
```

### Manual Configuration

### Stdio Transport (Recommended)

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "uvx",
      "args": ["--from", "/absolute/path/to/mcp-tradingview-server", "mcp-tradingview"]
    }
  }
}
```

Alternative with uv run:

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "uv",
      "args": ["run", "mcp-tradingview"],
      "cwd": "/absolute/path/to/mcp-tradingview-server"
    }
  }
}
```

### HTTP Transport

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "uv",
      "args": ["run", "mcp-tradingview", "--transport", "http", "--host", "0.0.0.0", "--port", "8001", "--path", "/mcp"],
      "cwd": "/absolute/path/to/mcp-tradingview-server"
    }
  }
}
```

Restart Claude Desktop after updating the configuration. The bundled `CLAUDE.md` provides extra guidance the model can reference while chatting.

## Development

- `uv run pytest` executes the asynchronous test suite in `test_server.py`.
- Use `logging.getLogger(__name__)` for diagnostics; avoid printing secrets.
- Refer to `export/` for captured fixtures when updating tests or documentation.

## License

This project is provided as-is for educational and research purposes.
