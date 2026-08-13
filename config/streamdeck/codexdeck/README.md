# Codex Deck

StreamController 1.5 plugin for the 15-key Stream Deck MK.2.

Layout:

- Top and middle rows: one deterministic list of up to ten Codex tmux panes,
  ordered by tmux session, window, and pane index. Focus and completion state
  never reorder the keys. Unacknowledged completed turns pulse in place until
  pressed; pressing any key selects its exact tmux pane and focuses Ghostty.
  `WORKING` reflects a real Codex active-turn inhibitor; the selected tmux pane
  is indicated by color instead of a potentially misleading text status.
- Bottom row: volume down/up, output mute, microphone mute, and a manual
  AirPods connect/disconnect toggle.

Codex's top-level `notify` command invokes `notify.py` after each completed
turn. The callback stores only identifiers, cwd, pane ID, and timestamp under
`$XDG_STATE_HOME/codex-deck`, together with the notification classification;
prompts, assistant messages, and subagent paths are discarded.
Root sessions also post a passive desktop notification without an action that
focuses Ghostty. Subagent and unclassified completions remain in the event log
for diagnostics but do not post desktop notifications.

The AirPods control calls BlueZ over D-Bus. It does not enable auto-connect.

New Codex sessions use the native `notify` callback. A live tmux-pane watcher
also records a durable attention event whenever an existing Codex process goes
from an active turn to waiting, so sessions started before the callback was
configured still pulse when they need attention.

Tmux focus hooks acknowledge a pending completion when its exact Codex pane is
actually viewed, whether selected with the keyboard, mouse, or Stream Deck.
Unfocused clients, non-Codex panes, and Codex panes without a pending completion
are ignored.

The actions self-assign StreamController's image, label, and background control
fields when a hand-authored page omits them. This keeps generated pages from
rendering as black keys.
