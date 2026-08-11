# Codex Deck

StreamController 1.5 plugin for the 15-key Stream Deck MK.2.

Layout:

- Top row: live launchers for up to five Codex tmux panes.
- Middle row: up to five completed Codex turns. Keys pulse until pressed, then
  select the exact originating tmux pane and focus Ghostty.
- Bottom row: volume down/up, output mute, microphone mute, and a manual
  AirPods connect/disconnect toggle.

Codex's top-level `notify` command invokes `notify.py` after each completed
turn. The callback stores only identifiers, cwd, pane ID, and timestamp under
`$XDG_STATE_HOME/codex-deck`; prompts and assistant messages are discarded. It
also posts a passive desktop notification without an action that focuses
Ghostty.

The AirPods control calls BlueZ over D-Bus. It does not enable auto-connect.

The actions self-assign StreamController's image, label, and background control
fields when a hand-authored page omits them. This keeps generated pages from
rendering as black keys.
