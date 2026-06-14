---
name: desktop-incident-triage
description: Triage this Framework Desktop's Hyprland, CachyOS, SDDM login, Ghostty/Chrome focus, workspace routing, Bluetooth, AirPods, PipeWire, media controls, and local desktop service incidents with live-state checks before changing config.
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
- Autostart belongs in `config/hypr/config/autostart.conf`.
- User placement and focus overrides belong in
  `config/hypr/config/user-overrides.conf`.
- Existing durable placement preferences include Ghostty on ws1, Chrome on ws2,
  Slack on ws3, Discord on ws4, and Steam on ws6 unless the user changes them.

## Tools

- Use `$screenshot` or `linux-computer-use` when visual state matters.
- Use `chrome-devtools` for Chrome tab/focus control when browser state is
  part of the incident.

## Output

Explain what failed, the live evidence, what changed if anything, validation,
and any follow-up that should become a durable desktop-health note.
