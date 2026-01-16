---
name: agent-team
description: Split a large repo task into file-scoped subtasks and delegate each to isolated Codex subagents via the Codex MCP server, then integrate, test, and have the judge merge worker branches into the main repo. Use when a repo task is big enough to parallelize across multiple workers.
---

# Agent Team

## Overview
Run a Planner -> Workers -> Judge pipeline that parallelizes repo changes across isolated worker clones and integrates the results.

## Run
- From repo root (or let Codex run):
  - `python3 ~/.codex/skills/agent-team/scripts/team.py --task "<PASTE THE LARGE TASK>"`

## Options
- `--max-workers 4`
- `--planner-model <model-name>`
- `--worker-model <model-name>`
- `--judge-model <model-name>`

## Behavior
1) Planner decomposes the goal into file-scoped subtasks with dependencies.
2) Each subtask runs in a new referenced clone.
3) Workers implement changes and commit.
4) Manager applies patches to an integration clone and runs verification commands.
5) Judge reviews the integration diff + logs and merges worker branches into the default branch of the main repo using separate remotes per worker.

## Output
Artifacts are written to:
  .codex/agent-team-runs/<timestamp>/
    integration/        # integration clone (branch with merged work)
    clones/<task-id>/   # per-worker referenced clones
    patches/            # patch files exported from workers
    logs/               # planner/worker/judge transcripts
    plan.json           # structured task plan
