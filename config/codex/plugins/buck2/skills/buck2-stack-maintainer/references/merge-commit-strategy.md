# Buck2 Merge-Commit Strategy

This mirrors the `sluongng/bazel-rbe` maintenance model.

The fork has two responsibilities split across two branches:

- `fork/stack`: the direct patch stack, rebased onto `origin/main`.
- `fork/main`: a merge-commit branch used by BuildBuddy Workflows.

For a stack tip `S` and upstream tip `U`, `fork/main` should point at merge
commit `M`:

```text
origin/main:  ... --- U
                    \
fork/stack:          s1 --- s2 --- S
                    /              \
fork/main:       previous           M
```

`M^1` is always `U`; `M^2` is `S`. This keeps upstream history as the first
parent while still testing the full fork stack.

For per-commit validation, create merge commits for each prefix:

```text
M1 = merge(U, s1)
M2 = merge(U, s2)
M3 = merge(U, s3)
```

Push them to `fork/main` sequentially with `--force-with-lease`, waiting for
BuildBuddy after each push. The final remote state keeps only the full-stack
merge commit as branch HEAD, while the earlier merge commits remain addressable
by SHA in BuildBuddy results.
If a polled BuildBuddy workflow fails after a prefix push, the maintainer
script restores `fork/main` to the previous head by default before exiting;
use `--leave-failed-main` only for deliberate manual debugging.

BuildBuddy fetches `buildbuddy.yaml` at the exact commit SHA being executed.
Prefix commits that predate the workflow setup therefore need the merge commit
to carry the workflow harness. The maintainer script amends each prefix merge
with the harness files from the rebased stack tip while preserving the merge
parents. This follows the bazel-rbe pattern where the merge commit may contain
CI-only edits, but `M^1` remains upstream and `M^2` remains the tested stack
prefix.

Before rewriting `fork/main`, create a backup branch such as
`backup/buck2-main-before-stack-sync-YYYYmmdd-HHMMSS`. The retired
`fork/sluongng/codex-bes` branch is not part of the maintenance workflow.

Invariant checks:

```bash
git rev-parse fork/main^1
git rev-parse origin/main
git rev-parse fork/main^2
git rev-parse fork/stack
```

The first two commands must match. The last two commands must match after the
final prefix has been published.
