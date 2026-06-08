# eToro API Plugin

Local Codex plugin for the official eToro Public API.

The plugin provides:

- A standalone etoro-api CLI backed by the official REST API at https://public-api.etoro.com.
- A Codex skill that tells future agents how to use the CLI safely.
- Credential handling that keeps eToro keys in local config or environment variables, not in prompts, command lines, or normal command output.
- Trading write commands for the official execution endpoints, gated by dry-run tickets and exact confirmation tokens.

## Install

    "${ETORO_API_PLUGIN_DIR:-$HOME/plugins/etoro-api}/scripts/install-local.sh"
    command -v etoro-api
    etoro-api --help

If the current shell does not include ~/.local/bin on PATH, use
~/.local/bin/etoro-api directly or run:

    export PATH="$HOME/.local/bin:$PATH"

## Credentials

The CLI supports credentials in this order:

1. ETORO_API_KEY and ETORO_USER_KEY environment variables.
2. ~/.config/etoro-api/config.json, created by etoro-api init.

Do not pass keys as command-line flags. Shell history, process listings, and agent logs can expose command-line arguments.

Recommended setup is interactive:

    etoro-api init
    etoro-api --json doctor

The config file is created with mode 0600. doctor reports only whether credentials are present and where they came from. It never prints the key values.

## JSON Policy

Under --json, successful read commands without --out return the API JSON body directly. Commands with --out return a small envelope:

    {
      "ok": true,
      "status": 200,
      "path": "/absolute/path/response.json",
      "bytes": 1234
    }

Errors return a stable envelope and never include configured credentials:

    {
      "ok": false,
      "error": {
        "type": "api_error",
        "message": "Unauthorized",
        "status": 401
      }
    }

For private portfolio data, prefer --out so full account payloads are written to disk instead of injected into the agent transcript.

## Common Commands

    etoro-api --json doctor
    etoro-api --json me --out data/raw/etoro/me.json
    etoro-api --json portfolio --account real --out data/raw/etoro/portfolio.json
    etoro-api --json pnl --account real --out data/raw/etoro/pnl.json
    etoro-api --json trade-history --min-date 2025-01-01 --out data/raw/etoro/trade-history.json
    etoro-api --json instrument-search --search-text SPY --limit 5
    etoro-api --json rates 123 456
    etoro-api --json snapshot --account real --trade-history-min-date 2025-01-01 --out data/raw/etoro/snapshots/latest

The raw escape hatch is read-only:

    etoro-api --json request get /api/v1/me

## Trading Writes

The CLI supports narrow trading write paths from the official API:

- Close an existing position at market rate:

      etoro-api --json trade close-position --account real --position-id 123 --instrument-id 456

- Open a new long or short market position:

      etoro-api --json trade open-market --account demo --instrument-id 456 --side long --amount 100 --no-stop-loss --no-take-profit

- Cancel a pending open, close, or market-if-touched order:

      etoro-api --json trade cancel-order --account real --kind close --order-id 789

These commands default to dry-run and send no network write. The dry-run prints the exact
`--confirm` token required for execution. To send the order, rerun with both `--execute` and
that exact `--confirm` token.

For selling an existing long position, use `trade close-position`. Do not use
`trade open-market --side short`; that opens a new short position instead of closing a long.
