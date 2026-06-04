# Global Codex Guidance

## Branches

When creating local Git branches for the user, use the `sluongng/` prefix.
Do not use `codex/` as a branch prefix.

## Subagents

Use subagents when they can materially advance the task in parallel without
blocking the main path. Use the default Codex subagent for independent,
bounded codebase questions; keep urgent blocking work local, and do not
spawn subagents for trivial lookups.
