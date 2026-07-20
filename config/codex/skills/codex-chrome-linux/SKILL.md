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
HOST_BIN="$(command -v codex-linux-extension-host || printf '%s' "$HOME/.local/bin/codex-linux-extension-host")"
"$HOST_BIN" --json doctor
```

2. If `manifest-json`, `manifest-origin`, or `manifest-host-path` is false,
install the Chrome native messaging manifest, then restart or trigger Chrome:

```bash
HOST_BIN="$(command -v codex-linux-extension-host || printf '%s' "$HOME/.local/bin/codex-linux-extension-host")"
"$HOST_BIN" --json install-manifest --host-path "$HOST_BIN"
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
codex-linux-extension-host --json profiles --include-tabs
codex-linux-extension-host --json tabs
codex-linux-extension-host --json history --limit 10
```

When multiple Chrome profiles may have the Codex extension enabled, run
`profiles` first and pass `--profile <selector>` to later commands. The
selector may be `default`, a bridge PID, a socket basename, or an
`extensionInstanceId`/prefix from `profiles`.

Before opening a URL, look for an existing tab to reuse. `navigate <url>`
without `--tab-id` creates a new session tab and can create a new Codex tab
group. If a suitable tab already exists, use `navigate <url> --tab-id <id>`.
If the tab is visible but not yet in the session, claim it first with
`claim-tab --tab-id <id>`.

6. Use browser-control commands only when requested: `create-tab`,
`claim-tab`, `navigate`, `attach`, `cdp`, `detach`, `name-session`,
`finalize-tabs`, and `turn-ended`.

7. Finalize session tabs after browser work, keeping only deliverable or
   handoff tabs. Use `handoff` for tabs that future turns should reuse; use
   `deliverable` only for tabs that should remain for user inspection but do
   not need browser-session reuse. Then release controls for the turn:

```bash
codex-linux-extension-host --json finalize-tabs --session codex-manual --turn nav --keep 123:handoff
codex-linux-extension-host --json turn-ended --session codex-manual --turn nav
```

## Examples

List tabs:

```bash
codex-linux-extension-host --json tabs --session codex-manual --turn inspect
codex-linux-extension-host --json tabs --profile default --session codex-manual --turn inspect
```

Reuse an existing tab when navigating:

```bash
codex-linux-extension-host --json claim-tab --tab-id 123 --session codex-manual --turn nav
codex-linux-extension-host --json navigate https://example.com --tab-id 123 --session codex-manual --turn nav
```

Create a new tab only when there is no suitable tab to reuse:

```bash
codex-linux-extension-host --json navigate https://example.com --session codex-manual --turn nav
```

Finalize the session, keeping a tab for handoff:

```bash
codex-linux-extension-host --json finalize-tabs --session codex-manual --turn nav --keep 123:handoff
codex-linux-extension-host --json turn-ended --session codex-manual --turn nav
```

Evaluate JavaScript after claiming, creating, or navigating a tab:

```bash
codex-linux-extension-host --json cdp --tab-id 123 Runtime.evaluate --params '{"expression":"document.title","returnByValue":true}' --session codex-manual --turn inspect
```

### Construct CDP parameters safely

Do not hand-embed nontrivial JavaScript inside shell-quoted `--params` JSON.
Selectors and scripts commonly contain single quotes, dollar signs, backticks,
or newlines that the shell can reinterpret before the CLI receives them.

When orchestrating through `functions.exec`, serialize the parameter object and
shell-quote the completed JSON value:

```javascript
const expression = `document.querySelector(
  "button[aria-label^='Time range selected:']"
)?.click()`;
const params = JSON.stringify({ expression, returnByValue: true });
const shellQuote = (value) =>
  "'" + value.replaceAll("'", "'\\''") + "'";

const result = await tools.exec_command({
  cmd: `codex-linux-extension-host --json cdp --tab-id 123 Runtime.evaluate --params ${shellQuote(params)} --session codex-manual --turn inspect`,
});
text(result);
```

Use the short inline `--params '{...}'` form only for simple expressions that
contain no conflicting shell syntax. If the CLI prints its own usage followed
by `unexpected argument '<word>'`, and that word came from the JavaScript, treat
it as shell tokenization rather than a missing CDP feature. Rebuild the command
with programmatic JSON serialization and quoting.

## Safety

Do not inspect cookies, passwords, local storage, or arbitrary Chrome profile
files. Do not run raw CDP commands against logged-in sites unless the user asks
for that browser action. Do not change the native messaging manifest to allow
another extension ID without explicit approval.
