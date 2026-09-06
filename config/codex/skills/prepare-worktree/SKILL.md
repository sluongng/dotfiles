---
name: prepare-worktree
description: "Create or audit Git worktrees and propagate required local context; distinguish manual/headless copying from Codex App .worktreeinclude and setup behavior."
---

# Prepare Worktree

Keep the primary checkout's unrelated changes untouched. Treat worktree creation,
local-context propagation, and task-specific setup as separate operations.

## Codex App Worktrees

Use a tracked `.worktreeinclude` in a repository when every Codex App-created
worktree for that repository needs stable ignored files. The App
copies those files without overwriting destinations before it runs the Local
Environment `[setup]` script.

The file is repository-scoped. Add it once to each repository that needs this
copy behavior; repositories without required local-only files do not need one.

Use `[setup]` for actual post-creation commands such as dependency bootstrap,
code generation, or repository-specific initialization. The script receives:

- `CODEX_SOURCE_TREE_PATH`: the source checkout selected by the App.
- `CODEX_WORKTREE_PATH`: the newly created worktree.

Do not invoke `prepare-worktree-context` from `[setup]` merely to recopy files
already named by `.worktreeinclude`.

## Manual and Headless Worktrees

The headless app-server does not apply `.worktreeinclude` itself. The caller that
runs `git worktree add` must invoke `prepare-worktree-context` immediately after
creation and before starting work in the new checkout.

1. Resolve and inspect both checkouts:

       git -C <repo> worktree list --porcelain
       git -C <primary> status --short --branch
       git -C <worktree> status --short --branch

2. Create the worktree when needed:

       git -C <primary> worktree add <path> <branch-or-ref>

3. Audit the declared and known local-only context without changing the target:

       prepare-worktree-context \
         --primary <primary> \
         --worktree <worktree> \
         --dry-run

4. Copy missing declared and known context after reviewing the audit:

       prepare-worktree-context \
         --primary <primary> \
         --worktree <worktree> \
         --apply

   The executable uses Git's ignore-pattern engine to copy ignored regular files
   matched by the primary checkout's `.worktreeinclude`. It also discovers
   untracked or ignored files named `user.bazelrc`, `.bazelrc.user`,
   `.buckconfig.local`, and `AGENTS.md`. It preserves metadata, never prints
   contents, never follows source or destination symlinks, and never overwrites
   an existing destination. It also accepts the App environment variables
   instead of explicit path arguments.

5. Inspect repo-specific ignored files not covered by `.worktreeinclude` or the
   known-name list.
   Copy only what the task needs, never print credential contents, and never
   overwrite tracked target files without explicit user direction.

6. Run a narrow readiness check such as `bazel info`, `buck2 root`, or
   `git status --short`, then report copied and intentionally skipped files.

## Safety

- Prefer copies over hardlinks for credentials-backed configuration. Editing a
  worktree copy must not mutate the primary checkout by inode.
- Treat `CODEX_SOURCE_TREE_PATH` as the App-selected source, not necessarily the
  repository's canonical primary checkout.
- Do not copy caches, build outputs, logs, editor state, or task scratch files
  unless the user explicitly requests them.
- Keep this skill for source selection, worktree lifecycle, extra-file judgment,
  and validation; the executable only handles deterministic declared- and
  known-file copying.
