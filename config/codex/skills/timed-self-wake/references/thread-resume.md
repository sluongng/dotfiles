# Thread Resume

Most timed wake-ups should start a new codex-automaton run with a
self-contained prompt. This is more reliable than assuming the future agent can
recover the full parent conversation.

Use a thread id only when the user explicitly wants the same thread reopened.
In that case:

- Capture the exact thread/session id before scheduling.
- Include codex resume --include-non-interactive <thread_id> in the future
  instructions, not just the TOML metadata.
- Prefer a tmux handoff for interactive resumes; non-interactive systemd runs
  are better for self-contained actions.
- Still embed the critical context, approvals, and guardrails in the prompt.
  The thread id is a convenience, not the safety boundary.

Before relying on an exact-thread wake, identify the current writer and a
supported ownership-release or handoff path. Ending a turn, waiting for a quota
reset, or leaving an interactive session idle does not establish that its writer
lease has been released. Lock-file existence alone does not establish ownership
either. If release cannot be arranged within the user's authorization, report
the same-thread continuation as blocked; prefer a self-contained new run when
the user has not required the original thread. A new run must still check task
ownership and completion before touching the saved worktree.

At firing, a resume rejection such as `already has an active writer` is a blocked
continuation, not successful task execution. Preserve its diagnostic/exit result;
do not kill the owner, remove locks, or silently switch threads to bypass it.
Timer installation and firing verify scheduling only. Verify the resumed task's
final result or completion receipt before claiming the continuation completed.

If the exact thread id is unavailable, do not guess. Ask the user for it or use
a self-contained codex-automaton prompt instead.
