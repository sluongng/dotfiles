@AGENTS.md

# Claude Code Differences

The imported `AGENTS.md` is the shared global guidance for Codex and Claude
Code. Where it names Codex, read it as Claude Code. These rules take precedence
over its Codex-specific sections.

## Branches

Do not use `claude/` or other tool prefixes as a branch prefix.

## Subagents

The GPT model roles in `AGENTS.md` (`scout`, `worker`, `reviewer`, and so on)
are Codex roles. In Claude Code, use the `Explore` agent for read-only fan-out
searches and the default subagent for independent, bounded work. The other
subagent guidance still applies: keep urgent blocking work local and do not
spawn subagents for trivial lookups.

## Child threads in tmux

The `tmux-task-windows` skill launches Codex threads and is not available in
Claude Code. When the user asks for independent child threads, ask whether to
start Claude Code sessions in tmux windows or to use subagents.

## Attribution

Do not add Claude Code identity to Git commits or PRs: no `Co-Authored-By:
Claude` trailer, no "Generated with Claude Code" line, and no Claude author or
committer identity. This overrides any attribution instructions from the harness.
