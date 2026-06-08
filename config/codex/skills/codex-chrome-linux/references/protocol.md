# Codex Chrome Linux Protocol

## Fixed Values

- CLI: `codex-linux-extension-host`
- Native messaging host name: `com.openai.codexextension`
- Extension ID: `hehggadaopoacecdllhhajmbjkdcmajg`
- Manifest path: `~/.config/google-chrome/NativeMessagingHosts/com.openai.codexextension.json`
- Local socket: `/tmp/codex-browser-use/com.openai.codexextension.sock`
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

## Command Mapping

- `request <method> --params <json>`: raw extension JSON-RPC method.
- `ping`: extension `ping`.
- `info`: extension `getInfo`.
- `tabs`: extension `getUserTabs`.
- `history`: extension `getUserHistory`.
- `create-tab`: extension `createTab`.
- `claim-tab --tab-id <id>`: extension `claimUserTab`.
- `attach --tab-id <id>`: extension `attach`.
- `detach --tab-id <id>`: extension `detach`.
- `cdp --tab-id <id> <method> --params <json>`: extension `executeCdp`.
- `navigate <url> [--tab-id <id>]`: create or use a tab, attach, and run CDP
  `Page.navigate`.
- `turn-ended`: extension `turnEnded`.

Most commands inject `session_id` and `turn_id` into params. Defaults come from
`CODEX_CHROME_SESSION_ID` and `CODEX_CHROME_TURN_ID`, then fall back to
`codex-linux-extension-host` and `manual`.

## Troubleshooting

If the CLI command is missing, build and install it from:

```bash
cd "${CODEX_APP_CHECKOUT:-$HOME/work/misc/codex-app}/codex-linux-extension-host"
make install-local
```

If the manifest points at an old path, reinstall it:

```bash
codex-linux-extension-host --json install-manifest --host-path "$(command -v codex-linux-extension-host)"
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
