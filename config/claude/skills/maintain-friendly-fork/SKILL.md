---
name: maintain-friendly-fork
description: "Maintain a friendly fork or long-lived patch stack by refreshing from the origin default branch when requested, rebasing local changes, detecting commits already merged upstream, validating every replayed commit with build/test commands, resolving conflicts without hiding failures, squashing newly added commits into the existing stack, regrouping or renumbering reviewable topic sets, checking tree equivalence for topic-only restacks, and force-pushing rewritten history to the tracked upstream branch with --force-with-lease when asked."
---

# Maintain Friendly Fork

## Goal

Update or restack a friendly fork while preserving a reviewable,
independently validated stack of local patches.

Use this skill when the user asks to refresh a fork, rebase a local stack,
drop patches that landed upstream, split or regroup fork-only commits, keep
topic branches reviewable after upstream moved, or publish a rewritten stack.
A task may be a full upstream refresh or a topic-only regrouping of the current
local commits.

## Operating Rules

- Inspect the repo state before changing history: remotes, current branch,
  dirty files, upstream default branch, merge base, and local-only commits.
- Do not rewrite a dirty worktree. Ask before stashing or committing unrelated
  work unless the user already gave explicit permission.
- Distinguish the requested operation. Do not change the branch base when the
  user only asked for topic regrouping or renumbering.
- Create a safety branch or tag before any history rewrite, with a name that
  identifies the operation, for example
  `backup/<branch>-before-upstream-rebase-<date>` or
  `backup/<branch>-before-topic-regroup-<date>`.
- Prefer the origin remote's default branch from `refs/remotes/origin/HEAD`.
  Fall back to `origin/main` or `origin/master` only when the default branch is
  not configured.
- Treat upstream-equivalent commits as dropped, not rewritten. Record their old
  subject and, when available, the matching upstream commit.
- Treat newly added local commits as stack material, not automatically as new
  review commits. Squash fixups into the commit they repair, or move real new
  steps into the right topic and renumber that topic.
- Before reordering commits, map cross-topic dependencies such as generated
  files, dependency declarations, imports, config includes, and local overlay
  files. Put prerequisites before dependents or move the prerequisite into the
  earliest commit that needs it.
- For topic-only restacks, verify final tree equivalence against the safety ref
  unless the user explicitly asked for content changes.
- If per-commit validation requires hiding local-only config or artifacts, save
  and restore them explicitly, and include the restoration in final checks.
- Validate every commit that remains in the stack independently. Do not finish
  with only a tip-of-branch test if intermediate commits can fail.
- When the user asks to push rewritten history, resolve the tracked upstream
  with `@{u}`, push to that exact remote/ref with `--force-with-lease`, and
  verify the remote-tracking ref matches `HEAD`.
- Keep final reporting concrete: old base, new base, commits dropped, commits
  rewritten, validation command, failures fixed, safety refs, publish target,
  local config restored, and residual risk.

## Workflow

1. Gather state.

   ```bash
   git status --short
   git remote -v
   git symbolic-ref --short refs/remotes/origin/HEAD
   git branch --show-current
   git merge-base HEAD origin/<default-branch>
   git log --oneline --reverse <base>..HEAD
   ```

   If `origin/HEAD` is missing, run `git remote set-head origin --auto` after
   `git fetch origin`, or inspect `git remote show origin`.

2. Fetch and identify upstream.

   ```bash
   git fetch origin --prune
   upstream=$(git symbolic-ref --short refs/remotes/origin/HEAD)
   ```

   Normalize `upstream` to a remote-tracking ref such as `origin/main`.

3. Detect upstreamed patches before rebasing.

   Use `git cherry -v "$upstream" HEAD` for patch-equivalence detection.
   Lines starting with `-` are already present upstream and should be dropped
   from the local stack. Use `git log --cherry-pick --right-only` or stable
   patch IDs when a more detailed match is needed.

4. Create a safety ref.

   ```bash
   git branch backup/<branch>-before-<operation>-$(date +%Y%m%d-%H%M%S)
   ```

5. Rebase with per-commit validation.

   Prefer `git rebase --exec '<validation command>' "$upstream"` so each picked
   commit is tested as soon as it is replayed. Add `--empty=stop` when
   supported so commits that become empty are inspected before they are skipped.
   Add `--rebase-merges` only if preserving a non-linear stack is intentional.

   If validation is expensive, use the narrowest command that proves the
   touched project still builds and tests. If no command is supplied, inspect
   repo docs, CI config, and package metadata, then state the selected command.

6. Handle conflicts and failed validation.

   When a conflict stops the rebase, resolve only the current commit's conflict,
   run that commit's validation command, and continue. When an exec step fails,
   fix the current commit with `git commit --amend --no-edit`, re-run the
   validation command, then continue the rebase.

   If a commit becomes empty, inspect whether upstream already contains the
   patch. Skip it only after confirming it is upstream-equivalent or made
   obsolete by an earlier replayed commit, and include it in the final dropped
   list.

7. Compare the old and new stacks.

   ```bash
   git range-diff <old-upstream>..<old-head> "$upstream"..HEAD
   git log --oneline --reverse "$upstream"..HEAD
   ```

   Use the range-diff to verify that intended patches survived and upstreamed
   patches disappeared.

8. Regroup commits when the stack is hard to review.

   Split the stack into topic sets that tell a coherent story. A topic set may
   contain one or more commits. Every commit must build and test on its own and
   should leave the tree in a sensible intermediate state.

   Honor user-provided topic anchors first. If an anchor is too large, split it
   into smaller subtopics with stable prefixes instead of flattening it. For
   example, a broad client topic may become transport, cache, chunking, and
   execution subtopics; a broad observability topic may become core publishing
   and format-conversion subtopics.

   Use the `draft-commit-message` skill for each final commit message. For a
   single-commit topic, use the repository's normal subject shape. For a
   multi-commit topic, choose a short topic name and number the commits:

   ```text
   [client foo 1/5]: prepare refactoring

   In a future change, this stack adds feature foo to the client code.
   Refactor the code and tests so field bar is available where the
   later client foo changes need it.
   ```

   Keep numbered subjects short, imperative, and reviewable. The body may refer
   to earlier or later commits in the topic when that makes the narrative
   clearer.

9. Integrate newly added commits into the stack.

   If the user has added commits on top of an existing friendly-fork stack,
   inspect whether each commit is a fixup, a missing test, a cleanup for an
   earlier change, or a real new review step. Prefer squashing fixups with
   `git commit --fixup=<target>` plus `git rebase --autosquash`, or by moving
   an existing commit next to its target in `git rebase -i` and marking it
   `fixup` or `squash`.

   If the new commit belongs in an existing multi-commit topic, move it into
   that topic, choose its order, and renumber every commit in the topic. Use
   `draft-commit-message` to reword affected messages so the topic still
   reads as a coherent sequence. Validate every rewritten commit after the
   squash or renumbering.

10. Final validation and report.

   Run the agreed final validation on the rebased branch tip, even if every
   commit was validated during rebase. Report exact commands and outcomes.

11. Publish a rewritten stack only when asked.

   Resolve the configured upstream before pushing:

   ```bash
   git status --short --branch
   git rev-parse --abbrev-ref --symbolic-full-name @{u}
   git remote -v
   ```

   Push with a lease to the exact upstream remote and branch, then verify that
   `HEAD` and the remote-tracking ref are identical.

## Details

Read [rebase-stack-workflow.md](references/rebase-stack-workflow.md) when you
need command variants for patch-equivalence checks, `git rebase --exec`,
autosquashing new commits into an existing stack, interactive regrouping, or
final reports.
