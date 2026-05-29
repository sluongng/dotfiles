---
name: etoro-api
description: Use when working with the official eToro Public API for portfolio snapshots, PnL, trade history, market data, instrument lookup, rates, candles, watchlists, social data, or approval-gated eToro trading automation through the local etoro-api CLI.
---

# eToro API

Use the installed etoro-api CLI for eToro API work. Do not hand-build authenticated curl commands unless the CLI is missing a read-only endpoint and the user explicitly asks for that raw call.

## Credential Safety

- Never ask the user to paste eToro keys into chat.
- Never print, summarize, copy, or cat ~/.config/etoro-api/config.json.
- Never pass keys through command-line flags; they can leak through shell history and process listings.
- Prefer etoro-api init run interactively by the user, or environment variables already present in the shell.
- Use etoro-api --json doctor to check whether credentials are available; it reports only source categories, not values.
- For private account payloads, prefer --out <path> so full portfolio data is written to disk instead of injected into model context.

## Start Here

Verify the command exists:

    command -v etoro-api || /home/nb/plugins/etoro-api/scripts/install-local.sh

If command lookup still fails because ~/.local/bin is not on PATH, use /home/nb/.local/bin/etoro-api directly or prepend PATH="$HOME/.local/bin:$PATH" for the command.

Check setup:

    etoro-api --json doctor

If auth is missing, ask the user to run this in their own terminal:

    etoro-api init

## Safe Read Path

For account collection, write raw API responses to files:

    etoro-api --json snapshot --account real --trade-history-min-date 2025-01-01 --out data/raw/etoro/snapshots/latest

For individual reads:

    etoro-api --json me --out data/raw/etoro/me.json
    etoro-api --json portfolio --account real --out data/raw/etoro/portfolio.json
    etoro-api --json pnl --account real --out data/raw/etoro/pnl.json
    etoro-api --json trade-history --min-date 2025-01-01 --out data/raw/etoro/trade-history.json

For public market-data lookup:

    etoro-api --json instrument-search --search-text SPY --limit 5
    etoro-api --json instruments --instrument-id 123
    etoro-api --json rates 123 456
    etoro-api --json candles 123 --interval OneDay --count 100

## Raw Escape Hatch

Use the raw command only for read-only API coverage gaps:

    etoro-api --json request get /api/v1/me

The CLI intentionally supports only GET and HEAD in request.

## Trading Writes

The plugin exposes narrow trading execution commands. These default to dry-run and send no network write:

    etoro-api --json trade close-position --account real --position-id 123 --instrument-id 456
    etoro-api --json trade open-market --account demo --instrument-id 456 --side long --amount 100 --no-stop-loss --no-take-profit
    etoro-api --json trade cancel-order --account real --kind close --order-id 789

Only execute after the user approves the exact ticket. Execution requires both:

    --execute
    --confirm <exact token from dry-run output>

For selling an existing long position, use trade close-position. Do not use
trade open-market --side short to sell an existing long; that opens a new short position.
Before closing a real position, fetch or inspect the real portfolio, identify the exact
positionId, instrumentId, and units, present the ticket to the user, and wait for approval.

Do not mutate watchlists, create social posts, or use arbitrary write endpoints unless the CLI
has been extended with the same dry-run and exact-confirmation behavior.
