---
name: bazel-target-open
description: Resolve Bazel labels from terminal output and open the matching BUILD file target with the local bazel-target-open CLI, especially when tmux-fingers selected labels such as //pkg:target or @repo//pkg:target.
---

# Bazel Target Open

Use the installed `bazel-target-open` CLI when the user wants to inspect or open
a Bazel label from terminal output.

Start by verifying the command and local state:

```bash
command -v bazel-target-open
bazel-target-open --json doctor
```

The CLI is local/offline and does not use auth. It resolves labels relative to
the current working directory's Bazel workspace.

For read-only inspection, prefer:

```bash
bazel-target-open --json resolve //foo:bar
printf '%s\n' '@repo//foo:bar' | bazel-target-open --json resolve
```

Before live editor actions while debugging, preview the command:

```bash
printf '%s\n' //foo:bar | bazel-target-open --json open --dry-run
```

Live opens are intentional UI actions. Only run `bazel-target-open open` when
the user asked to open the target or when wiring an interactive tmux-fingers
flow. Inside tmux, it opens a new tmux window; outside tmux, it runs the editor
attached to the current terminal.

Use the raw snippets only for integration work:

```bash
bazel-target-open raw regex
bazel-target-open raw tmux-binding --key B
```

Do not modify `.tmux.conf` or install/reinstall the CLI unless the user asks for
configuration or setup changes.
