# Codex Deck

StreamController 1.5 plugin for the 15-key Stream Deck MK.2.

Layout:

- Top two rows: a deterministic list of up to ten Codex tmux panes, ordered by
  tmux session, window, and pane index. Focus and completion state never reorder
  the keys. Unacknowledged completed turns pulse in place until pressed;
  pressing any key selects its exact tmux pane and focuses Ghostty.
  `WORKING` reflects a real Codex active-turn inhibitor; the selected tmux pane
  is indicated by color instead of a potentially misleading text status. The
  selected idle pane has a slow breathing edge-light, working panes use a
  faster circulating highlight, and completed turns use a distinct double
  pulse. Empty and inactive panes stay static so the deck does not become a
  wall of motion. Occupied keys show the thread's current working-directory
  name in the center.
- Bottom row:
  1. Toggle local, system-wide dictation. The first press records from the
     default PipeWire/ALSA microphone; the second press transcribes locally with
     Whisper and inserts the result into the input where recording began. You
     can move through other tmux panes or applications while speaking. A tmux
     origin receives the transcript directly in its exact pane without changing
     the current desktop focus. Dictation must begin in a Ghostty/tmux input;
     Chrome and other applications can be used as references while recording,
     but are not accepted as destinations because Wayland cannot reliably
     restore an exact child input control. If the original tmux target
     disappeared or changed commands, the transcript is withheld instead of
     being typed into the wrong input. The action starts the `voxtype` user
     service if necessary, reflects recording/transcription state on the key,
     and never injects Enter, so dictated text remains editable. Multiline or
     tabbed text requires the original application to have enabled bracketed
     paste; otherwise the transcript is retained for recovery. Terminal control
     characters are also withheld instead of being sent as keyboard commands.
  2. Send a physical Enter key through `ydotool` to the currently focused
     input. This is deliberately separate from dictation so the transcript can
     be reviewed or edited before submitting it in Codex CLI/tmux, Chrome, a
     game, or another application.
  3. Choose a trusted project from the private
     `~/.codex/projects.local.toml` file, create a zsh window in the most
     recently active attached tmux session, start Codex in that directory, and
     select its exact pane before focusing Ghostty. Project paths are read only
     at runtime and never copied into this repo.
  4. Toggle play/pause for the active MPRIS media player.
  5. Manually connect or disconnect AirPods.

The checked-in `page.json` is the canonical 15-key layout. The live
StreamController page is
`~/.var/app/com.core447.StreamController/data/pages/first.json`.
Run `./install-page.sh` from this directory to back up that live page, install
the canonical layout, and restart StreamController.

Dictation uses the AVX-512 Voxtype release binary at `~/.local/bin/voxtype`, the
tracked configuration at `~/.config/voxtype/config.toml`, and the tracked
`voxtype.service` user unit. `./install-dictation.sh` installs the pinned,
checksum-verified binary, links the tracked files, downloads the local
`base.en` model, and enables the daemon. Each Stream Deck recording writes to a
mode-`0700` runtime directory instead of typing globally. The plugin then pastes
the finished text directly into the exact captured tmux pane. Clipboard fallback
is disabled so clipboard history cannot retain dictated text. Successful and
empty recordings are removed; a transcript is retained only when delivery
fails, with a local recovery notification. The user service denies all IP
networking, suppresses process logs, and disables core dumps, keeping normal
dictation local and ephemeral.

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
