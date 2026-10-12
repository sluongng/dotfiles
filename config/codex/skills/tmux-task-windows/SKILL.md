---
name: tmux-task-windows
description: Launch independent Codex child threads in tmux with a fire-and-forget handoff, or present existing task results in a tmux window when requested or useful.
---

# Tmux task windows

Make independent work and its results available in stable, named tmux windows.
Launching a child is complete once startup and handoff are verified; the child
owns its work and final answer. Do not turn a launch request into a monitoring
task. This skill does not itself authorize creating child threads or expanding
their work beyond the user's request.

## Launch independent work

- Inspect the current tmux session and window names. Reuse the intended session;
  create a detached window so the user's selected window stays unchanged. If
  the user requested a new thread, start a fresh thread rather than resuming an
  older route. For an existing task, reuse its route when appropriate.
- Prepare a brief containing the objective, exact repository and source links,
  expected result, relevant prior evidence, and authorized changes. Preserve the
  requested scope: an implementation task stays implementation, while a request
  to summarize review comments stays analysis. Tell the child to present its
  final answer in its own thread. Keep private handoffs outside public source.
- Create the window first and launch the interactive Codex TUI from `zsh -lic`.
  Pass the working directory explicitly to BOTH tmux (`-c`) and Codex (`--cd`);
  the shared app-server can otherwise use a different directory from the pane.
  Use the shared endpoint `--remote unix://` on this installation. Inherit the
  user's model, reasoning, and permission settings unless instructed otherwise.
- For a saved idle thread, use `codex resume --remote unix:// --cd <repo>
  --include-non-interactive <thread-id>`. Never stop or interrupt an active
  writer to move it into tmux or attach another writer to the same thread.
  Present an existing live window, or defer resumption until that turn ends.
- Keep the login shell as the TUI's parent, and leave a shell after Codex exits.
  The intended process chain is `tmux -> zsh -lic -> codex`. Build commands with
  proper shell quoting (for example, Python `shlex.join`/`shlex.quote`), not JSON
  escaping. Prefer a brief in a local file over a large prompt pasted as shell
  code. Avoid interpolating untrusted text into commands.
- Give each window a short task-specific name. Disable automatic window rename
  for that window if needed to preserve it. Do not change session-wide options.

## Startup and handoff

Do one bounded startup check: confirm the expected process chain, repository
directory, inherited `EDITOR`/`VISUAL`, and that the prompt reached the intended
TUI. Fix an immediate launch error within scope. If it is still initializing,
report that accurately; do not wait for analysis or the first substantive result.

Record the session/window, pane, repository, brief, and thread ID when readily
available. Use supported thread metadata first; blank/truncated metadata is not
a reason to poll repeatedly or inspect broad session history. A verified tmux
window plus its brief is a usable handoff while the thread ID is unavailable.
Update an existing task ledger only when that is part of the current workflow.

Return a concise list of the windows and what each child will deliver. Continue
independent parent work or end the turn. Do not wait for completion, repeatedly
capture panes, summarize intermediate findings, or send extra follow-up prompts
unless the user requests monitoring/results or the parent must integrate them.
Report "started" separately from "completed".

## Present results in tmux

- For a request to show results "next to this pane", identify the pane running
  the task's thread from a verified thread/process mapping. The user's active
  tmux client or window may have changed and is not a reliable task anchor.
  Target the verified pane explicitly when splitting or moving panes; do not
  guess the target from whichever window is currently selected.
- If the task already has a window, identify it for the user. Select it only
  when the user asks to switch or show it now; otherwise preserve focus.
- To show a saved report, diff, or log, open a clearly named detached result
  window at the artifact's directory, using a readable pager such as `less`.
  Keep the report's source path and freshness clear. Do not start another model
  run just to display an existing artifact, or rerun work to manufacture output.
- Keep the canonical review artifacts ANSI-free and editor-friendly: use
  Markdown for narrative reports and `.diff` for full patches. If terminal
  color is requested, provide a separately labeled pager rendering (for example,
  viewed with `less -R`), not the only copy or the file recommended for Neovim.
- If no artifact exists and the user asks for a result view, save only the
  relevant user-facing answer to an appropriate local file and open that file.
  Do not include hidden reasoning, raw credentials, or unrelated conversation.
- Use an interactive Codex window when the user needs to continue the task;
  use a pager when they only need to read its result. A log or pager window is
  not a substitute for a requested interactive child thread.

Verify only that the intended artifact or thread is visible, then return its
window name and route. Never close or replace another running task's window.

## Change directory for subsequent panes

When the user wants new panes to open in a task's worktree, distinguish Codex's
session working directory from the running pane's process directory and tmux's
`pane_current_path`. Updating thread settings or using `cd` in a tool command
does not establish that tmux will split into the new directory. Inspect the
actual split/new-window binding and its directory selection. Prefer an explicit
`-c <worktree>` or a pane-scoped solution without restarting an active writer or
changing other panes' behavior. Verify the directory of an actual new pane or
window through the intended workflow before reporting it fixed; preserve the
user's selected window and clean up only verification panes created for this
check.
