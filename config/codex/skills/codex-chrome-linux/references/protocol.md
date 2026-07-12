# Codex Chrome Linux Protocol

## Fixed Values

- CLI: `codex-linux-extension-host`, or
  `$HOME/.local/bin/codex-linux-extension-host` when the Codex shell PATH does
  not include `$HOME/.local/bin`
- Native messaging host name: `com.openai.codexextension`
- Extension ID: `hehggadaopoacecdllhhajmbjkdcmajg`
- Manifest path: `~/.config/google-chrome/NativeMessagingHosts/com.openai.codexextension.json`
- Legacy/default local socket: `/tmp/codex-browser-use/com.openai.codexextension.sock`
- Additional Chrome profile sockets:
  `/tmp/codex-browser-use/com.openai.codexextension.<pid>.sock`
- Active bridge registry: `/tmp/codex-browser-use/bridges/*.json`
- Native framing: 4-byte little-endian length followed by a JSON message
- Local protocol: JSON-RPC 2.0 over the same length-prefixed framing

## Doctor Checks

- `platform`: true only on Linux.
- `manifest-json`: the Chrome native messaging manifest exists and parses.
- `manifest-origin`: the manifest allows
  `chrome-extension://hehggadaopoacecdllhhajmbjkdcmajg/`.
- `manifest-host-path`: the manifest `path` points at an executable.
- `chrome-extension-installed`: a Google Chrome profile contains an extension
  directory matching the Codex extension ID.
- `bridge-socket-ping`: the local Unix socket accepts `host.ping`.
- `extension-ping`: the extension responded through Chrome native messaging.

`bridge-socket-ping` can be true while `extension-ping` is false when the host
is running but Chrome has not connected the extension yet.

Multiple Chrome profiles can run their own native-host instances. The first
instance uses the legacy/default socket. Later instances fall back to per-PID
sockets and write registry entries so CLI callers can discover them with
`profiles`.

## Command Mapping

- `request <method> --params <json>`: raw extension JSON-RPC method.
- `ping`: extension `ping`.
- `info`: extension `getInfo`.
- `profiles`: list active Chrome profile bridge instances, their sockets, and
  extension metadata when available.
- `tabs`: extension `getUserTabs`.
- `history`: extension `getUserHistory`.
- `create-tab`: extension `createTab`.
- `claim-tab --tab-id <id>`: extension `claimUserTab`.
- `attach --tab-id <id>`: extension `attach`.
- `detach --tab-id <id>`: extension `detach`.
- `cdp --tab-id <id> <method> --params <json>`: extension `executeCdp`.
- `navigate <url> [--tab-id <id>]`: attach and run CDP `Page.navigate`.
  When `--tab-id` is omitted, this creates a new session tab; it does not look
  for an existing tab with the same URL or origin.
- `name-session <name>`: extension `nameSession`.
- `finalize-tabs [--keep <tab-id>[:handoff|deliverable]]...`: extension
  `finalizeTabs`.
- `turn-ended`: extension `turnEnded`.

Most commands inject `session_id` and `turn_id` into params. Defaults come from
`CODEX_CHROME_SESSION_ID` and `CODEX_CHROME_TURN_ID`, then fall back to
`codex-linux-extension-host` and `manual`.

Most commands accept `--socket-path PATH` for exact socket selection or
`--profile SELECTOR` for active bridge selection. `--profile` selectors can be
`default`, a bridge PID, a socket basename, or an `extensionInstanceId`/prefix
shown by `profiles`.

## Tab Reuse

The CLI does not automatically reuse existing Chrome tabs. To avoid opening a
new Codex tab group, inspect tabs first, choose a tab ID, then pass that ID to
`claim-tab`, `navigate`, `attach`, or `cdp`:

```bash
codex-linux-extension-host --json profiles --include-tabs
codex-linux-extension-host --json claim-tab --tab-id 123 --session codex-manual --turn nav
codex-linux-extension-host --json navigate https://example.com --tab-id 123 --session codex-manual --turn nav
```

At the end of a turn, keep reusable tabs as handoff tabs:

```bash
codex-linux-extension-host --json finalize-tabs --session codex-manual --turn nav --keep 123:handoff
codex-linux-extension-host --json turn-ended --session codex-manual --turn nav
```

Tabs kept as `deliverable` are intended for user inspection, not session reuse.
Tabs kept as `handoff` are the right choice when a later Codex turn should
continue controlling or navigating the same browser tab.

## Troubleshooting

If the CLI command is missing, build and install it from:

```bash
cd "${CODEX_APP_CHECKOUT:-$HOME/work/misc/codex-app}/codex-linux-extension-host"
make install-local
```

If the manifest points at an old path, reinstall it:

```bash
HOST_BIN="$(command -v codex-linux-extension-host || printf '%s' "$HOME/.local/bin/codex-linux-extension-host")"
"$HOST_BIN" --json install-manifest --host-path "$HOST_BIN"
```

If `bridge-socket-ping` is false, Chrome has not started the native host or the
socket was removed. Restart Chrome, then trigger the Codex extension. For host
debugging outside Chrome, run:

```bash
codex-linux-extension-host native-host
```

If Chrome extension storage or `chrome://extensions` reports `Native host has
exited.`, verify the installed host can run with Chrome's native-messaging
launch argument:

```bash
codex-linux-extension-host 'chrome-extension://hehggadaopoacecdllhhajmbjkdcmajg/'
```

That command should keep listening until interrupted. If it prints
`unrecognized subcommand`, rebuild and reinstall the host from
`${CODEX_APP_CHECKOUT:-$HOME/work/misc/codex-app}/codex-linux-extension-host`.

If `extension-ping` is false but `bridge-socket-ping` is true, the local host is
alive but it is not connected to the Chrome extension side.

If more than one Chrome profile is open, discover the active bridge instances:

```bash
codex-linux-extension-host --json profiles --include-tabs
codex-linux-extension-host --json tabs --profile default
codex-linux-extension-host --json tabs --profile 5261faf0
```
