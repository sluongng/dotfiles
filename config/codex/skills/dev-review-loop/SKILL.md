---
name: dev-review-loop
description: Iteratively finish an active development task by implementing in the main thread, launching clean-room subagent code reviews of the total diff against the target branch, fixing all valid findings, repeating until no findings remain, then committing with draft-commit-message. Use when the user asks Codex to finish a coding task end-to-end with independent review loops before commit.
---

# Dev Review Loop

## Goal

Finish the current development task in the main thread, validate it, run an
independent clean-room review of the full branch diff, fix review findings, and
repeat until no actionable findings remain. Commit only after the review loop is
clean.

## Preconditions

- Respect current system and developer instructions. Use subagents only when
  they are allowed and the user has requested this workflow.
- Keep all implementation work in the main thread. Subagents review only.
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
- Review the total intended change, not only the last commit.

2. Implement the task in the main thread.

Read the relevant code before editing. Make the narrowest change that completes
the user request. Follow local style and existing abstractions.

Run focused validation after implementation. Prefer the smallest representative
test first, then broaden when the touched behavior is shared or user-facing.

3. Launch a clean-room review subagent.

Spawn exactly one bounded review subagent for each review round. Use minimal
forked context when possible, such as `fork_turns="none"` or the smallest useful
recent context. Do not pass your implementation rationale, suspected bugs, or
desired outcome except where needed to understand the task.

Use a prompt shaped like:

```text
You are reviewing a completed implementation in <repo path>.

Task:
<original user task, concise>

Target branch:
<target branch or merge base>

Review the total intended diff against the target branch, including committed
changes and any staged/unstaged worktree changes. Take a code-review stance:
prioritize correctness bugs, race conditions, regressions, missing validation,
and test gaps. Do not edit files. Return findings first, ordered by severity,
with file/line references and concrete reasoning. If there are no actionable
findings, say that clearly and mention residual test risk.
```

4. Triage review findings.

When the subagent returns findings:

- Validate each finding against the live code.
- Fix all valid findings in the main thread.
- If a finding is invalid, document the reason briefly.
- Rerun relevant formatting and tests after fixes.
- Do not let the review subagent patch the code.

Repeat the review loop after every fix round. Continue until the latest
clean-room review reports no actionable findings.

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

Rerun the strongest practical validation command used during the task. Separate
smoke checks from representative validation in the final report.

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
- review-loop result and number of review rounds
- validation commands and outcomes
- final commit hash and subject
- any residual risk or skipped validation
