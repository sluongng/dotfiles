# Rebase Stack Workflow

## Preflight Commands

Prefer direct machine-state checks over assumptions:

```bash
git status --short
git rev-parse --show-toplevel
git branch --show-current
git remote -v
git fetch origin --prune
git symbolic-ref --short refs/remotes/origin/HEAD
git remote show origin
```

Resolve the upstream default branch:

```bash
upstream=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD || true)
if [ -z "$upstream" ]; then
  git remote set-head origin --auto
  upstream=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD || true)
fi
```

If this still fails, choose `origin/main` or `origin/master` only after checking
which ref actually exists:

```bash
if git show-ref --verify --quiet refs/remotes/origin/main; then
  upstream=origin/main
elif git show-ref --verify --quiet refs/remotes/origin/master; then
  upstream=origin/master
fi
```

Record the old stack:

```bash
branch=$(git branch --show-current)
old_head=$(git rev-parse HEAD)
old_upstream=$(git merge-base HEAD "$upstream")
git log --oneline --reverse "$old_upstream"..HEAD
git branch "backup/${branch}-before-upstream-rebase-$(date +%Y%m%d-%H%M%S)"
```

For a topic-only regroup, preserve the current base and make the operation name
explicit:

```bash
branch=$(git branch --show-current)
old_head=$(git rev-parse HEAD)
old_upstream=$(git merge-base HEAD "$upstream")
git branch "backup/${branch}-before-topic-regroup-$(date +%Y%m%d-%H%M%S)"
```

## Detect Upstreamed Commits

Use patch-equivalence before rebasing:

```bash
git cherry -v "$upstream" HEAD
```

Interpretation:

- `+ <sha> <subject>` means the patch is not present upstream.
- `- <sha> <subject>` means upstream already has an equivalent patch.

For more detail, compare patch IDs:

```bash
git show <local-sha> | git patch-id --stable
git log "$upstream" --format=%H -- <paths> |
  while read sha; do git show "$sha" | git patch-id --stable; done
```

When a commit is upstreamed, prefer dropping it from the stack and telling the
user exactly which local commit disappeared. If the matching upstream commit is
known, include it in the report.

## Rebase With Per-Commit Validation

Choose a validation command before rewriting:

- Use the user-specified build/test command when provided.
- Otherwise inspect repo-local docs, task runners, CI config, and package
  manifests.
- Prefer a narrow per-project command during rebase and a broader final command
  after the stack is rebuilt.

Common command shapes:

```bash
git rebase --no-update-refs --empty=stop --exec '<validation command>' "$upstream"
git rebase --empty=stop --exec '<validation command>' "$upstream"
git rebase --reschedule-failed-exec --empty=stop --exec '<validation command>' "$upstream"
git rebase --rebase-merges --empty=stop --exec '<validation command>' "$upstream"
```

When `--empty=stop` is unavailable, inspect any empty-commit or skipped-commit
messages manually before continuing.

If an exec validation fails:

```bash
# inspect and fix the current commit
git status --short
<validation command>
git add <fixed-files>
git commit --amend --no-edit
<validation command>
git rebase --continue
```

If the failure is caused by commit reordering, fix the earliest commit that now
needs the missing dependency. Examples include moving an import to the commit
that first uses it, moving generated dependency rules before code that references
them, or moving a config file before an include is introduced.

If a conflict occurs:

```bash
git status --short
# resolve only the current commit's conflict
git add <resolved-files>
<validation command>
git rebase --continue
```

Do not skip a conflicted commit unless it is confirmed upstream-equivalent,
obsolete, or the user explicitly asks to drop it.

## Isolate Local Validation State

Per-commit validation can be invalidated by local config or artifacts that are
not part of the stack. Before validating, inspect local overlays and generated
outputs that the build command reads.

If a local config file includes files that appear only in later commits, hide it
for the validation rebase and restore it afterward:

```bash
saved=
if [ -e .toolconfig.local ]; then
  mv .toolconfig.local .toolconfig.local.claude-validation-saved
  saved=.toolconfig.local.claude-validation-saved
fi

git rebase --no-update-refs --empty=stop --exec '<validation command>' "$upstream"

if [ -n "$saved" ] && [ -e "$saved" ]; then
  mv "$saved" .toolconfig.local
fi
```

Use the repo's real local-config filename. On failure or interruption, restore
the saved file before ending the turn unless it is still needed for immediate
manual validation. Final checks should prove the local file is back and the
temporary saved file is gone.

## Regroup a Stack Into Topics

Inspect the current stack:

```bash
git log --oneline --reverse "$upstream"..HEAD
git diff --stat "$upstream"..HEAD
```

Use interactive rebase, soft reset, or fixup commits depending on the shape of
the stack:

```bash
git rebase -i "$upstream"
git reset --soft "$upstream"
git add -p
git commit
```

Topic grouping rules:

- Group by review topic, not file path alone.
- Honor topic anchors supplied by the user. If the user asks for all changes
  related to one integration, product, protocol, or subsystem to stay together,
  keep that as the outer topic boundary.
- Split an oversized topic into coherent subtopics with a stable prefix instead
  of mixing it back into unrelated commits. Good split axes include transport
  vs cache vs execution, core plumbing vs format conversion, config vs example,
  or generated prerequisites vs user-facing behavior.
- Keep mechanical prep, behavior changes, tests, and cleanup separate when that
  makes review easier.
- Fold pure fixups into the commit they repair.
- Reorder commits so prerequisites appear before dependent changes.
- Before moving a commit earlier, inspect its imports, dependency declarations,
  generated files, config includes, and local-only overlay files. If a moved
  commit now needs a later prerequisite, either move that prerequisite earlier
  or amend the moved commit so it remains independently buildable.
- Validate each commit after regrouping, not only after the final commit.

For multi-commit topics, use short numbered subjects:

```text
[scheduler routing 1/3]: expose pool metadata
[scheduler routing 2/3]: route actions by pool
[scheduler routing 3/3]: test pool fallback
```

Use `$draft-commit-message` for each message body. The body should explain why
the commit exists and may point to earlier or later commits in the same topic.

After a topic-only regroup, check whether the final tree is intentionally the
same as before the rewrite:

```bash
git range-diff "$old_upstream".."$old_head" "$old_upstream"..HEAD
git diff --stat "$old_head"..HEAD
git diff --quiet "$old_head"..HEAD
```

An empty tree diff means the rewrite only changed commit boundaries, order, or
messages. If the tree differs, report the intentional content change or stop and
inspect the accidental drift.

## Squash New Commits Into an Existing Stack

When the user added commits after the stack was already shaped, first decide
whether each new commit deserves to remain standalone:

- Squash typo fixes, review fixups, missing tests, mechanical cleanup, and
  follow-up changes that only repair an earlier commit.
- Move real new behavior into the matching topic if it extends an existing
  topic.
- Keep a new standalone commit only when it introduces a separate reviewable
  step with its own motivation.

For uncommitted changes that repair an earlier commit:

```bash
git add <files>
git commit --fixup=<target-sha>
git rebase -i --autosquash --exec '<validation command>' "$upstream"
```

With autosquash, validate the resulting squashed commits in the final stack.
Temporary `fixup!` commits do not need to stand alone because they disappear
before review.

For an existing top-of-stack commit that should be folded into an earlier
commit:

```bash
git log --oneline --reverse "$upstream"..HEAD
git rebase -i --autosquash --exec '<validation command>' "$upstream"
```

In the todo list, move the new commit directly after its target and mark it
`fixup` when the target commit message should stay, or `squash` when the
combined commit message needs to be edited. If the new commit should amend the
message as well as the diff, use `git commit --fixup=amend:<target-sha>` when
creating it, or mark the target `reword` in the interactive todo.

If autosquash is not enough, do a manual interactive rebase:

```bash
git rebase -i "$upstream"
# reorder commits, change pick to fixup/squash, and mark affected commits reword
git rebase -i --exec '<validation command>' "$upstream"
```

After any squash, run a range-diff against the safety ref and verify that the
final stack contains the same intended patch content without the temporary
fixup commits:

```bash
git range-diff "$old_upstream".."$old_head" "$upstream"..HEAD
```

## Move New Commits Into a Numbered Topic

When a new commit belongs in an existing numbered topic:

1. Identify the topic span and target position.
2. Use `git rebase -i "$upstream"` to move the commit into that span.
3. Mark every commit in the topic as `reword`.
4. Rename subjects from `[topic i/N]: ...` to the new total `N`.
5. Update bodies that refer to earlier or later commits so the narrative still
   matches the new order.
6. Run per-commit validation with `git rebase -i --exec '<validation command>'`
   or another explicit commit-by-commit validation loop.

Example after adding a new second step:

```text
[client foo 1/6]: prepare refactoring
[client foo 2/6]: expose bar accessors
[client foo 3/6]: add foo request plumbing
[client foo 4/6]: handle foo responses
[client foo 5/6]: test foo failures
[client foo 6/6]: document foo behavior
```

Use `$draft-commit-message` for each reworded commit. Keep the topic name short
and stable unless the added commit changes the topic's purpose.

## Final Checks

Run these after the rebase/regrouping is complete:

```bash
git range-diff "$old_upstream".."$old_head" "$upstream"..HEAD
git log --oneline --reverse "$upstream"..HEAD
git status --short
<final validation command>
```

For a topic-only regroup, also run:

```bash
git diff --quiet "$old_head"..HEAD
```

If commit messages were generated or rewritten through `$draft-commit-message`,
run that skill's validator across the final stack when available.

Report:

- Upstream base before and after.
- Local commits before and after.
- Commits dropped because upstream already had them.
- New commits squashed into earlier stack entries.
- Topics that were reordered or renumbered.
- Conflicts encountered and how they were resolved.
- Per-commit validation command and final validation command.
- Safety ref names and whether local validation overlays were restored.
- Any skipped tests, partial validation, or assumptions.

## Publish Rewritten History

Only force-push after the user asks. Resolve the branch's tracked upstream; do
not assume it is `origin`.

```bash
git status --short --branch
git rev-parse --abbrev-ref HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git remote -v
```

If the upstream is `fork/topic-branch`, push with a lease to that exact ref:

```bash
git push --force-with-lease fork HEAD:topic-branch
```

Then verify local and remote-tracking refs match:

```bash
git rev-parse HEAD
git rev-parse @{u}
git status --short --branch
```
