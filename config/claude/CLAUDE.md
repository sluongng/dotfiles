# Global Claude Code Guidance

## Branches

When creating local Git branches for the user, use the `sluongng/` prefix.
Do not use `claude/` or other tool prefixes as a branch prefix.

## Subagents

Use subagents (the `Agent` tool) when they can materially advance the task in
parallel without blocking the main path. Use the `Explore` agent for read-only
fan-out searches and the default subagent for independent, bounded codebase
questions; keep urgent blocking work local, and do not spawn subagents for
trivial lookups.
