---
name: buck2-stack-maintainer
description: Maintain the Buck2 BuildBuddy patch stack in /home/nb/work/facebook/buck2 by rebasing fork/stack onto origin/main, publishing bazel-rbe-style merge commits to fork/main with origin/main as first parent, triggering or polling BuildBuddy Workflows, and fixing failed stack commits.
---

# Buck2 Stack Maintainer

Use this skill for the Buck2 fork stack in `/home/nb/work/facebook/buck2`.
The durable stack branch is `fork/stack`; `fork/sluongng/codex-bes` is retired
except as a bootstrap or recovery source. The public CI branch is `fork/main`.

## Invariants

- `origin/main` is the upstream source of truth.
- `fork/stack` is the linear review stack rebased onto `origin/main`.
- `fork/main` is a merge-commit branch. Its HEAD must be a non-FF merge commit
  where `HEAD^1 == origin/main` and `HEAD^2 == fork/stack`.
- Do not delete or rewrite old branches without an explicit backup ref and a
  lease. Preserve unrelated dirty or untracked files.
- Validate stack prefixes in order. If prefix N fails, fix the corresponding
  stack commit with fixup/autosquash, then rerun from that prefix.

## Standard Workflow

1. Inspect state before mutating anything:

   ```bash
   git status --short --branch
   git remote -v
   git ls-remote --heads fork main stack sluongng/codex-bes
   ```

   In automation worktrees, ensure only `.buckconfig.local` is linked from the
   primary checkout before using `--wait-buildbuddy`:

   ```bash
   ln -s /home/nb/work/facebook/buck2/.buckconfig.local .buckconfig.local
   ```

2. Dry-run the maintainer script from the Buck2 checkout. For the first
   migration, use `--source-ref HEAD` if the local checkout has commits not yet
   present on the retired remote branch.

   ```bash
   python3 /home/nb/.dotfiles/config/codex/plugins/buck2/skills/buck2-stack-maintainer/scripts/sync_stack.py \
     --dry-run \
     --source-ref HEAD
   ```

3. Check BuildBuddy setup before any branch rewriting. This verifies the
   current `fork/main` merge-parent invariant and tries the workflow preflight
   against the current merge commit:

   ```bash
   python3 /home/nb/.dotfiles/config/codex/plugins/buck2/skills/buck2-stack-maintainer/scripts/sync_stack.py \
     --check-buildbuddy-setup
   ```

   If this reports that `sluongng/buck2` is not known to BuildBuddy, stop and
   complete the GitHub App / Workflows setup from
   `references/buildbuddy-workflows.md` before pushing more merge commits.
   After GitHub App access has been granted, use
   `scripts/buildbuddy_link_repo_browser.py` to link the repo through the
   logged-in BuildBuddy browser session, then rerun the setup check.

4. Apply locally in an isolated automation worktree or a deliberately prepared
   checkout. Use the bootstrap flag only until `fork/stack` exists:
   Use `--source-ref <sha-or-ref>` whenever the source should be an explicit
   local stack tip rather than the current `fork/stack` remote branch.

   ```bash
   python3 /home/nb/.dotfiles/config/codex/plugins/buck2/skills/buck2-stack-maintainer/scripts/sync_stack.py \
     --apply \
     --source-ref HEAD
   ```

5. Publish only after reviewing the plan and local invariants. This pushes
   stack-prefix merge commits to `fork/main` sequentially and updates
   `fork/stack` at the end:

   ```bash
   python3 /home/nb/.dotfiles/config/codex/plugins/buck2/skills/buck2-stack-maintainer/scripts/sync_stack.py \
     --apply --push --wait-buildbuddy \
     --source-ref HEAD
   ```

6. On failure, inspect the BuildBuddy invocation and the stack commit that
   introduced it. Prefer the existing Buck2 validation helpers:

   ```bash
   buildbuddy/run_stack_test_matrix.sh --from origin/main --to HEAD --mode remote --matrix app-rust
   buildbuddy/run_buck2_test_matrix.sh --mode both --matrix app-rust --clean-output
   ```

## References

- Read `references/merge-commit-strategy.md` before changing the branch model
  or force-pushing `fork/main`.
- Read `references/buildbuddy-workflows.md` before changing workflow trigger or
  polling behavior.
