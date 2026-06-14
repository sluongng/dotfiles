---
name: personal-skill-review
description: Review recent Claude Code session logs for repeated issues involving dotfiles-managed personal skills, then update or add a personal skill only when the evidence is concrete and recurring. Use for "scan recent sessions for skill issues", "should this become a skill?", or recurring automation runs that maintain personal skills.
---

# Personal Skill Review

Use this skill when the task is to inspect recent Claude Code activity and decide whether a dotfiles-managed personal skill should be added or improved.

Keep the scope tight:

- Personal skills only: `${DOTFILES_DIR:-$HOME/.dotfiles}/config/claude/skills`.
- Ignore repo-local skills and Claude's built-in skills/plugins unless they are only being used as tooling
- Default to no-op when recent logs do not show repeated, actionable friction

## Workflow

1. Read prior memory first (see Memory below) if this is a recurring or scheduled run.
2. Scan only recent session JSONL files, usually the last day, under `~/.claude/projects`.
3. Extract real failures from tool outputs and assistant commentary. Prefer `jq` plus focused `rg` filters over broad grep.
4. Separate skill-related friction from generic task failures. Only count an issue when a skill would realistically prevent or shorten the failure next time.
5. Check whether the problem is already covered by an existing personal skill or prior memory.
6. If a fix is warranted, keep changes minimal and targeted. If a new workflow keeps recurring and does not fit an existing skill, create a new personal skill.
7. Validate edited skills, reinstall dotfiles-managed skills, and report whether the run was a no-op or what changed.

## Evidence Rules

Treat these as good reasons to update or add a skill:

- The same path, command-shape, or environment mistake recurs across multiple recent runs
- A skill exists but its instructions missed an important guardrail
- The agent repeatedly reconstructs the same multi-step workflow from scratch

Do not update skills for:

- One-off shell mistakes with no sign of recurrence
- Failures caused by unrelated repo state or missing external services
- Generic coding mistakes that are not skill-amenable

## Session Scan Pattern

Start with a narrow inventory:

```bash
find "$HOME/.claude/projects" -type f -mtime -1 | sort
```

Then inspect message/tool payloads with `jq` and focused filters. Favor patterns such as `Process exited with code`, `No such file or directory`, `failed`, `not found`, `unsupported`, and known skill names.

When reviewing outputs, explicitly ignore noise caused by:

- Searching the logs for the word `skill` and matching the prompt itself
- Historical examples copied out of memory files
- Expected non-zero exits used as existence checks

## Memory

For recurring runs, persist findings in Claude's file-based memory rather than a
bespoke automation file. The memory for a project lives under
`~/.claude/projects/<project-slug>/memory/`, indexed by `MEMORY.md`. Read
`MEMORY.md` first to recall what previous reviews already flagged, and append a
short note (with the date) for anything new you decide. This avoids re-flagging
the same friction every run.

## Editing Rules

- Keep write scope to the affected personal skill directory when possible
- Do not overwrite unrelated dirty worktree changes
- Prefer creating a new skill only when the workflow is recurring and clearly reusable
- Keep `SKILL.md` concise; add scripts or references only if they remove repeated boilerplate or fragile command construction

## Validation

After editing personal skills, sanity-check each changed `SKILL.md` and
reinstall the dotfiles-managed skills so the `~/.claude` symlinks are current:

```bash
dotfiles_dir="${DOTFILES_DIR:-$HOME/.dotfiles}"
skill="$dotfiles_dir/config/claude/skills/<skill-name>/SKILL.md"

# SKILL.md must exist and have YAML frontmatter with a name and description.
test -f "$skill"
head -n1 "$skill" | grep -qx -- '---'
grep -qE '^name:' "$skill"
grep -qE '^description:' "$skill"

"$dotfiles_dir/automation/claude/install-claude.sh"
```

Keep the `description` specific and trigger-oriented — it is what Claude uses to
decide when to load the skill. If nothing changed, say so explicitly and record
the no-op in memory when this is a recurring run.
