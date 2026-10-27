---
name: dev-review-loop
description: "Finish a coding task with independent Codex and Claude Code reviews and fixes when the user requests review loops before committing."
---

# Dev Review Loop

## Goal

Finish the current development task in the main thread, validate it, run
independent clean-room reviews of the full branch diff with both Codex and
Claude Code, fix review findings, and repeat until neither reviewer has
actionable findings. Commit only after the review loop is clean.

## Preconditions

- Run this workflow from Codex. Claude Code is an external reviewer, not the
  orchestrator; do not replace the configured Codex reviewer with a Claude
  subagent.
- Respect current system and developer instructions. Use subagents only when
  they are allowed and the user has requested this workflow.
- Keep all implementation work in the main thread. Both reviewers review only.
- Check that the `claude` CLI is available and authenticated. If either reviewer
  cannot complete, report the blocker; do not silently use only one reviewer or
  treat a failed review as clean.
- Preserve unrelated user changes. Do not stage, revert, or rewrite files that
  are outside the task.
- If the target branch is unclear, infer it from PR metadata, upstream tracking,
  or the repo default branch. Ask only if inference is risky.

## Workflow

1. Establish state.

Run:

```bash
git status --short
git branch --show-current
git remote -v
```

Identify the target branch for the total diff. Prefer, in order:

- the PR base branch when a PR is active
- the branch configured as the upstream merge base
- `origin/main`, `origin/master`, or the repo default branch

Compute the merge base:

```bash
git merge-base HEAD <target-branch>
git diff --stat <merge-base>...HEAD
git diff --stat <merge-base>
```

Use the correct diff form for the current state:

- Include committed task changes since the merge base.
- Include staged and unstaged worktree changes.
- Include intended untracked files explicitly; `git diff` does not show them.
- Review the total intended change, not only the last commit.

2. Implement the task in the main thread.

Read the relevant code before editing. Make the narrowest change that completes
the user request. Follow local style and existing abstractions.

Run validation appropriate to the affected behavior and required repository
checks. Broaden testing when a failure or unresolved risk warrants it.

3. Launch two independent clean-room reviews.

For each round, run these reviewers in parallel when possible:

- **Codex:** spawn one `reviewer` subagent with `fork_turns="none"` and a
  self-contained brief. Use the role's configuration from
  `config/codex/agents/reviewer.toml` in the dotfiles repo, without model or
  reasoning effort overrides.
- **Claude Code:** start a fresh non-interactive `claude` process in the repo,
  using its default configuration. Do not use `--continue` or `--resume`.

Let Codex's reviewer-role configuration and Claude Code's normal configuration,
both managed by the dotfiles repo, select their settings. Do not hardcode models,
reasoning effort, permissions, tools, or integrations in this skill or override
them in review invocations. Future dotfiles configuration changes should apply
without editing this workflow.

Give both reviewers the same task, exact merge base, intended file scope, and
current total diff. Keep the reviewed tree unchanged until both finish. Do not
pass implementation rationale, suspected bugs, desired outcomes, or the other
reviewer's findings except where needed to understand the task.

Record HEAD, index/worktree diffs, and intended untracked file contents before
the round and verify they are unchanged afterward. If either reviewer changes
them, stop and inspect the unexpected changes; do not declare the round clean
or automatically discard the changes.

Use a shared prompt shaped like:

```text
You are reviewing a completed implementation in <repo path>.

Task:
<original user task, concise>

Target branch and exact merge base:
<target branch and merge-base commit>

Intended file scope:
<task files; identify unrelated changes to exclude>

Review the total intended diff against the target branch, including committed,
staged, unstaged, and intended untracked files. Take a code-review stance:
prioritize correctness bugs, race conditions, regressions, missing validation,
and test gaps. Do not edit files, commit, publish, or delegate further. Return
findings first, ordered by severity, with file/line references and concrete
reasoning. If there are no actionable findings, say that clearly and mention
residual test risk.
```

For Claude Code, save the brief and full diff (`git diff <merge-base>`, scoped
only when needed to exclude unrelated work), plus intended untracked file
contents, in a temporary input file outside the repo:

```bash
cd <repo-path>
claude --print < <review-input-file> > <claude-review-output-file>
```

Keep the output file outside the repo too. Allow the process to finish, using
the execution tool's session/wait mechanism when it yields a running process;
do not treat a still-running review as a failed or completed one. Check the exit
status and read its result; authentication errors, tool denials that prevent
review, and incomplete output are blockers, not findings-free reviews. The
read-only review assignment does not authorize edits or external writes,
regardless of the tools and permissions available through the default
configuration.

4. Triage review findings.

After both reviewers finish:

- Combine and deduplicate their findings, retaining reviewer attribution.
- Validate each finding against the live code.
- Fix all valid findings in the main thread.
- If a finding is invalid, document the reason briefly.
- Rerun relevant formatting and tests after fixes.
- Do not let either reviewer patch the code.

Repeat both clean-room reviews after every fix round. Continue until both
reviews of the same final tree report no actionable findings, with any disputed
findings explicitly resolved below.

If the same disputed finding repeats, resolve it explicitly with source
evidence. If progress is blocked by missing requirements or an untestable
environment, report the blocker instead of committing.

5. Final validation.

Before committing, run:

```bash
git status --short
git diff --stat
git diff --check
```

Reuse passing validation on the final code state. Rerun affected checks after
changes or when an unresolved concern warrants it; an unchanged tree does not
need another full run merely because review finished. Separate smoke checks
from representative validation in the final report.

6. Commit with draft-commit-message.

Load and follow `$draft-commit-message`.

Stage only intended task files:

```bash
git add <intended files>
git diff --cached --stat
git diff --cached
```

Draft the commit message from the staged diff and task context. Validate the
message with the skill's validator when available.

Create a new commit unless the user explicitly requested an amend or the active
task context clearly says to amend the current patch.

Use one of:

```bash
git commit -F <message-file>
git commit --amend -F <message-file>
```

After committing, verify:

```bash
git status --short
git log -1 --oneline
```

## Final Response

Report:

- what changed
- review-loop result and number of paired review rounds, with each reviewer's
  outcome and the models used when reported
- validation commands and outcomes
- final commit hash and subject
- any residual risk or skipped validation
