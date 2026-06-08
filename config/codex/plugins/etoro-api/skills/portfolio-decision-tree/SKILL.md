---
name: portfolio-decision-tree
description: Build live portfolio updates, catalyst decision trees, fee-aware sizing, and approval-gated eToro trade tickets from fresh broker state, market data, and local notes without executing trades unless the exact ticket is explicitly approved.
---

# Portfolio Decision Tree

Use this for portfolio updates, event timing, allocation decisions, and
trade/no-trade calls in the local stock-analysis repo, usually
`${STOCK_REPO:-$HOME/work/misc/stock}`. Use `$etoro-api` for the raw broker CLI
mechanics.

## Fresh State First

- Run `etoro-api --json doctor` before private reads.
- Prefer writing private payloads to disk under the repo rather than injecting
  full account data into context.
- Refresh portfolio, PnL, trade history, and relevant quotes or candles before
  giving current-state advice.
- If aggregate `snapshot` fails but individual `portfolio`, `pnl`, and
  `trade-history` reads work, continue from the individual files.
- Check local notes under `data/private/notes/`, then `reports/`, then raw
  snapshot or individual read directories.

## Decision Tree Shape

For each trade or no-trade call, produce:

- current sleeve/exposure constraint
- catalyst or event being evaluated
- evidence gate to buy/add, hold, reduce, or wait
- sizing cap and fee/spread impact
- exact next review condition or date

Use subagents for parallel research when the user asks for broad event or thesis
coverage, then synthesize a single action tree.

## Trading Safety

- Default to decision support and ticket preparation, not execution.
- Do not place real orders without explicit approval of the exact ticket.
- For existing long positions, use `trade close-position`; do not open a short
  to sell an existing long.
- For real writes, use the CLI dry-run, present the confirm token and ticket,
  wait for approval, execute with `--execute --confirm <token>`, then verify with
  fresh broker state. The write response alone is not proof of fill.
- Include broker fees, spreads, market-hours freshness, and concentration risk
  in sizing.

## Remembered Defaults To Recheck

- Do not add more `QQQ` from the China cleanup by default unless the user changes
  that plan.
- Treat "load up" questions as concentration and catalyst checks, not as an
  invitation to endorse a large add.
- Similar crypto-buy questions should default to a small staged entry from idle
  cash unless the user explicitly wants a bigger crypto sleeve.

## Output

Return the refreshed state source, decision tree, concrete trade or no-trade
call, exact dry-run ticket when relevant, required approval wording, and
post-write verification plan.
