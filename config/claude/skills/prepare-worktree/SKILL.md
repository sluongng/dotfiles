---
name: prepare-worktree
description: Prepare or audit Git worktrees for Claude automation, scheduled/background agents, long-running tasks, or isolated branch work. Use when Claude needs to create a worktree, refresh a worktree, make a worktree ready for unattended execution, or replicate local-only context such as AGENTS.md, user.bazelrc, .bazelrc.user, .buckconfig.local, credentials-backed build config, editor/tooling config, or repo-specific ignored files from a primary checkout.
---

# Prepare Worktree

Use this skill to make a Git worktree behave like the normal checkout before
starting automation or background agent work. A Git worktree shares Git object
state, but it does not automatically bring along untracked or ignored local files.

## Workflow

1. Identify the primary checkout and target worktree.
   - Use this command to find existing worktrees:

         git -C <repo> worktree list --porcelain

   - Treat the normal checkout as the source of local-only context unless the
     user names a different source.
   - Keep unrelated dirty changes in the primary checkout untouched.

2. Create or refresh the worktree.
   - Prefer this command for new worktrees:

         git worktree add <path> <branch-or-ref>

   - If reusing an existing worktree, inspect git status --short there before
     changing it.
   - Keep automation work on an explicit branch or detached ref that matches the
     requested task.

3. Audit local-only files in the primary checkout before running automation.
   - Run:

         git -C <primary> status --porcelain=v1 --untracked-files=all

   - Also inspect ignored-but-important files with targeted checks, for example:

         git -C <primary> ls-files --others --ignored --exclude-standard -- user.bazelrc .bazelrc.user .buckconfig.local AGENTS.md

   - Search for nested agent context files with:

         find <primary> -name AGENTS.md -type f

   - Decide which untracked or ignored files are required for the target worktree.

4. Link required local files into the worktree.
   - For a dry-run audit or repeatable automation setup, use the bundled helper:

         python3 <skill>/scripts/link_local_context.py --primary <primary> --worktree <worktree> --dry-run
         python3 <skill>/scripts/link_local_context.py --primary <primary> --worktree <worktree> --apply

   - Prefer hardlinks for regular files on the same filesystem:

         ln <primary-relative-file> <worktree-relative-file>

   - Fall back to symlinks when hardlinks fail or when linking directories:

         ln -s <source> <dest>

   - Prefer links over copies so API key or token rotations in one checkout are
     visible to other worktrees.
   - Create missing parent directories first.
   - Do not print credential file contents.

5. Give special treatment to build and agent-context files.
   - Link Bazel local config such as user.bazelrc and .bazelrc.user by default
     when present in the primary checkout; these often enable Remote Build
     Execution or remote cache credentials.
   - Link Buck2 local config such as .buckconfig.local by default when present in
     the primary checkout; it may contain remote execution, authentication, or
     local platform settings.
   - Link untracked or ignored AGENTS.md files by default when present in the
     primary checkout; they provide task-critical context for agents operating
     below that directory.
   - Do not overwrite a tracked file in the target worktree unless the user
     explicitly asks. If a tracked AGENTS.md already exists there, leave it and
     only add missing local-only context files.

6. Validate readiness.
   - Use ls -li <source> <dest> to confirm hardlinks share an inode.
   - Use readlink <dest> or readlink -f <dest> to confirm symlinks.
   - Run a narrow repo-appropriate sanity check when practical, such as bazel
     info, buck2 root, or git status --short.
   - Report the linked files and any intentionally skipped local files.

## Link Selection

Prefer hardlinks for secret-bearing regular files because they avoid path
fragility and keep changes synchronized by inode. Use symlinks when hardlinks are
impossible across filesystems, when the source is a directory, or when the target
should always point at the primary checkout current path.

Avoid linking generated outputs, caches, logs, editor swap files, or task-specific
scratch files unless the user explicitly requests them.

## Automation Notes

Prepare worktrees conservatively for unattended runs:

- Verify credentials-backed local config exists before scheduling background work.
- Preserve the primary checkout untracked files; replicate only what the target
  worktree needs.
- Prefer idempotent linking commands that detect existing destinations and compare
  them before replacement.
- Record assumptions in the final response so future scheduled agents know which
  checkout supplied the local context.

## Resources

- scripts/link_local_context.py: discover special local-only files in a primary
  checkout, then dry-run or create hardlinks/symlinks into a target worktree
  without printing file contents.
