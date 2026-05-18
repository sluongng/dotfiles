---
name: codex-chrome-linux
description: Inspect, instrument, and control Linux Google Chrome through the local Codex Chrome Extension native messaging bridge. Use when Codex needs Chrome tabs, history, navigation, Chrome DevTools Protocol commands, native host manifest/socket troubleshooting, or a Linux browser-control path instead of Chrome DevTools MCP.
---

# Codex Chrome Linux

Use `codex-linux-extension-host` as the only interface to the Codex Chrome
Extension bridge. It talks to the Chrome native messaging host over a local
Unix socket and returns JSON for Codex turns.

Read `references/protocol.md` when setup, method names, fixed paths, or
troubleshooting details matter.

## Workflow

1. Verify the CLI and bridge health:

```bash
command -v codex-linux-extension-host
codex-linux-extension-host --json doctor
```

2. If `manifest-json`, `manifest-origin`, or `manifest-host-path` is false,
install the Chrome native messaging manifest, then restart or trigger Chrome:

```bash
codex-linux-extension-host --json install-manifest --host-path "$(command -v codex-linux-extension-host)"
```

3. Confirm the Codex Chrome Extension is installed and enabled. Extension ID:
`hehggadaopoacecdllhhajmbjkdcmajg`. Web Store URL:

```text
https://chromewebstore.google.com/detail/codex/hehggadaopoacecdllhhajmbjkdcmajg
```

4. Use stable IDs for operations that touch tabs:

```bash
export CODEX_CHROME_SESSION_ID="codex-linux"
export CODEX_CHROME_TURN_ID="manual"
```

5. Prefer read-only probes first:

```bash
codex-linux-extension-host --json info
codex-linux-extension-host --json tabs
codex-linux-extension-host --json history --limit 10
```

6. Use browser-control commands only when requested: `create-tab`,
`claim-tab`, `navigate`, `attach`, `cdp`, `detach`, and `turn-ended`.

7. Release controls after browser work:

```bash
codex-linux-extension-host --json turn-ended
```

## Examples

List tabs:

```bash
codex-linux-extension-host --json tabs --session codex-manual --turn inspect
```

Navigate with a session tab:

```bash
codex-linux-extension-host --json navigate https://example.com --session codex-manual --turn nav
```

Evaluate JavaScript after claiming, creating, or navigating a tab:

```bash
codex-linux-extension-host --json cdp --tab-id 123 Runtime.evaluate --params '{"expression":"document.title","returnByValue":true}' --session codex-manual --turn inspect
```

## Safety

Do not inspect cookies, passwords, local storage, or arbitrary Chrome profile
files. Do not run raw CDP commands against logged-in sites unless the user asks
for that browser action. Do not change the native messaging manifest to allow
another extension ID without explicit approval.
