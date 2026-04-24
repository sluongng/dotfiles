# Global Codex Guidance

## Subagents

Use subagents when they can materially advance the task in parallel without
blocking the main path. Prefer `explorer` subagents for independent, bounded
codebase questions; keep urgent blocking work local, and do not spawn
subagents for trivial lookups.
