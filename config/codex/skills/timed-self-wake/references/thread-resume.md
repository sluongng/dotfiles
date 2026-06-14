# Thread Resume

Most timed wake-ups should start a new codex-automaton run with a
self-contained prompt. This is more reliable than assuming the future agent can
recover the full parent conversation.

Use a thread id only when the user explicitly wants the same thread reopened or
when an interactive handoff is the goal. In that case:

- Capture the exact thread/session id before scheduling.
- Include codex resume --include-non-interactive <thread_id> in the future
  instructions, not just the TOML metadata.
- Prefer a tmux handoff for interactive resumes; non-interactive systemd runs
  are better for self-contained actions.
- Still embed the critical context, approvals, and guardrails in the prompt.
  The thread id is a convenience, not the safety boundary.

If the exact thread id is unavailable, do not guess. Ask the user for it or use
a self-contained codex-automaton prompt instead.
