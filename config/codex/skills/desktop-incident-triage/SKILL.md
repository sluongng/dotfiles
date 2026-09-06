---
name: desktop-incident-triage
description: "Diagnose Framework Desktop incidents involving CachyOS, Hyprland, login, window focus, Bluetooth audio, or local services from live state."
---

# Desktop Incident Triage

Use this for local desktop incidents on the Framework Desktop. Work from live
state first, then make the smallest config or service change that matches the
evidence.

## Start With Live State

- For Hyprland: inspect `hyprctl configerrors`, `hyprctl binds`, `hyprctl clients
  -j`, active workspace, and the effective config files.
- For services: inspect `systemctl --user status`, relevant `journalctl --user`
  logs, and process state before restarting anything.
- For login or tty issues: inspect `loginctl`, SDDM journal lines,
  `getty@tty1.service`, `/etc/sddm.conf`, and current VT placement.
- For Bluetooth audio: inspect `bluetoothctl`, `wpctl status`, `pactl list
  cards short`, and whether a real PipeWire `bluez_card` or sink exists.

## Local Preferences

- Preserve iPhone-first AirPods ownership. Do not make the desktop auto-own or
  auto-reconnect AirPods unless the user explicitly asks.
- BlueZ "connected" is not enough for audio; verify PipeWire card/sink state.
- Prefer narrow config or logging changes for healthy services. Avoid restarts
  unless the service is unhealthy or the user wants interruption.
- The desired desktop default is a login screen, not SDDM autologin.
- Non-interactive sudo may not be available. Do not assume passwordless sudo.

## Hyprland Paths

- Dotfile-managed Hyprland config lives under
  `${DOTFILES_DIR:-$HOME/.dotfiles}/config/hypr`.
- Hyprland's compositor entrypoint is `config/hypr/hyprland.lua`.
- Autostart belongs in `config/hypr/config/autostart.lua`.
- Window placement and focus rules belong in
  `config/hypr/config/windowrules.lua`.
- Existing durable placement preferences include Ghostty on ws1, Chrome on ws2,
  Slack on ws3, Discord on ws4, and Steam on ws6 unless the user changes them.

## Hyprland Lua Control Plane

- This host uses Hyprland's Lua configuration and typed dispatcher API. Keep
  read-only `hyprctl` queries such as `clients -j`, `activewindow -j`,
  `configerrors`, and `binds`; express compositor mutations with Lua.
- Never use legacy dispatcher payloads such as `hyprctl dispatch workspace 1`,
  `focuswindow`, `closewindow`, `movetoworkspace`, or legacy `keyword`/`--batch`
  mutations. They are parsed as Lua on this host and fail with errors such as
  `')' expected`.
- For a durable change, edit the tracked Lua config and use `hl.dsp.*`,
  `hl.config`, `hl.monitor`, or another typed `hl.*` API directly. For a
  one-time action, use `hyprctl eval`, for example:
  `hyprctl eval 'return hl.dispatch(hl.dsp.focus({ workspace = 1 }))'` or
  `hyprctl eval 'return hl.dispatch(hl.dsp.focus({ window = "class:^(com.mitchellh.ghostty)$" }))'`.
- Resolve unfamiliar actions from the installed-version API stub at
  `/usr/share/hypr/stubs/hl.meta.lua` and the working examples under
  `/usr/share/hypr/hyprland.lua`; do not translate an old Hyprland command from
  memory. Validate persistent edits with `luac -p`, `Hyprland --verify-config`,
  and `hyprctl configerrors` before invoking the changed action.
- Before finishing Hyprland work, scan the relevant config and desktop scripts
  for `hyprctl dispatch`, `hyprctl keyword`, and `hyprctl --batch`. Treat every
  relevant hit as requiring review and convert legacy payloads to typed Lua.

## Tools

- Use `$screenshot` or `$linux-computer-use` when visual state matters.
- Use the official Chrome plugin for tab-level browser state when it is
  available. Use `$linux-computer-use` for Chrome window placement, focus, or
  extension-connection incidents that require desktop-level evidence.

## Output

Explain what failed, the live evidence, what changed if anything, validation,
and any follow-up that should become a durable desktop-health note.
