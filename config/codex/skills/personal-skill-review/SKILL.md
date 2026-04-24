---
name: personal-skill-review
description: Review recent Codex session logs for repeated issues involving personal skills under ~/.dotfiles/config/codex/skills, then update or add a personal skill only when the evidence is concrete and recurring. Use for "scan recent sessions for skill issues", "should this become a skill?", or recurring automation runs that maintain personal skills.
---

# Personal Skill Review

Use this skill when the task is to inspect recent Codex activity and decide whether a dotfiles-managed personal skill should be added or improved.

Keep the scope tight:

- Personal skills only: `/Users/sluongng/.dotfiles/config/codex/skills`
- Ignore repo-local skills and built-in `.system` skills unless they are only being used as tooling
- Default to no-op when recent logs do not show repeated, actionable friction

## Workflow

1. Read the automation memory first if the task is an automation run.
2. Scan only recent session JSONL files, usually the last day, under `~/.codex/sessions`.
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
find "$HOME/.codex/sessions" -type f -mtime -1 | sort
```

Then inspect message/tool payloads with `jq` and focused filters. Favor patterns such as `Process exited with code`, `No such file or directory`, `failed`, `not found`, `unsupported`, and known skill names.

When reviewing outputs, explicitly ignore noise caused by:

- Searching the logs for the word `skill` and matching the prompt itself
- Historical examples copied out of memory files
- Expected non-zero exits used as existence checks

## Automation Memory Path

When a run needs automation memory, do not assume `CODEX_HOME` is set. Resolve the path defensively:

```bash
AUTOMATION_BASE="${CODEX_HOME:-$HOME/.codex}/automations"
MEMORY_PATH="$AUTOMATION_BASE/<automation_id>/memory.md"
```

If the file exists, read it first. If the task requires writing the automation memory, use the resolved fallback path rather than raw `$CODEX_HOME/...`.

## Editing Rules

- Keep write scope to the affected personal skill directory when possible
- Do not overwrite unrelated dirty worktree changes
- Prefer creating a new skill only when the workflow is recurring and clearly reusable
- Keep `SKILL.md` concise; add scripts or references only if they remove repeated boilerplate or fragile command construction

## Validation

After editing personal skills:

```bash
python3 /Users/sluongng/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/sluongng/.dotfiles/config/codex/skills/<skill-name>
/Users/sluongng/.dotfiles/automation/codex/install-codex.sh
```

If `quick_validate.py` fails with `ModuleNotFoundError: No module named 'yaml'`,
do not stop there. Validate in a throwaway venv instead:

```bash
tmpdir="$(mktemp -d)"
python3 -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/pip" install PyYAML
"$tmpdir/venv/bin/python" /Users/sluongng/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/sluongng/.dotfiles/config/codex/skills/<skill-name>
rm -rf "$tmpdir"
```

If nothing changed, say so explicitly and record the no-op in automation memory when the task is an automation run.
