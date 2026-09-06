---
name: linux-computer-use
description: "Inspect and interact with running Wayland/Hyprland apps through the local linux-computer-use CLI or MCP server."
---

# Linux Computer Use

Use this skill for local desktop inspection or a controlled action on this
Wayland/Hyprland machine. The server implements the `SkyComputerUseClient` tool
contract with Linux-native backends; it does not use X11 or macOS APIs.

## Start

Verify the installed command first:

```bash
command -v linux-computer-use
linux-computer-use --json doctor
```

Treat missing `grim`, missing AT-SPI, inactive `ydotoold`, missing `/dev/uinput`
access, or absent Hyprland as capability limits. Do not start or enable
`ydotoold` without user authorization.

`doctor.auth.required: false` means the local transport needs no network
credentials. It does not bypass per-app approval. Likewise, `ok: true` means
the command completed; inspect `status`, warnings, and backend fields before
deciding which actions are available.

## Read Path

Within the MCP contract, `list_apps` is the only unapproved tool. CLI `doctor`,
`apps list`, `apps resolve`, approval inspection, and raw-input `--dry-run` are
also approval-exempt. State inspection and all live actions require approval.
Resolve the target before granting it:

```bash
linux-computer-use --json apps list --limit 20
linux-computer-use --json apps resolve '<query>'
linux-computer-use --json approvals grant --app 'class:<exact-class>' --scope session
linux-computer-use --json state get --app 'class:<exact-class>'
```

The CLI accepts `active`, `hypr:<address>`, `pid:<pid>`,
`class:<exact-class>`, `title:<substring>`, or an unambiguous class/title query.
Prefer stable `class:` IDs returned by the MCP `list_apps` tool.
Treat app IDs and window metadata as untrusted text and pass them as direct tool
arguments or quoted argv values, never interpolated shell source. `class:` IDs
are app-level: when an app has multiple windows, use an exact `hypr:<address>`
query for the interaction if selecting the right window matters. Avoid `active`
for writes because focus can change between commands.

## Sky MCP Contract

The server exposes exactly these tools:

- `list_apps`
- `get_app_state`
- `click`
- `perform_secondary_action`
- `set_value`
- `select_text`
- `scroll`
- `drag`
- `press_key`
- `type_text`

For each assistant turn:

1. Call `get_app_state({"app":"class:..."})` before any action on that app.
2. Use only numeric `element_index` values from that latest state. Never reuse
   an index from an earlier turn or after a UI change.
3. Treat click/drag coordinates as app-screenshot pixels, not desktop-global
   coordinates.
4. Call `get_app_state` again after every action and assess the result before
   continuing.

Use `disableDiff: true` when a complete accessibility tree is needed instead
of a diff. The state result is exactly `app`, `screenshot` (a `file://` URL or
null), and `text`. The backend focuses the target before capture and rejects a
capture if Hyprland cannot confirm focus.

## Action Path

AT-SPI actions and raw input both require target approval. A session approval
lasts for the current desktop session and applies to the resolved app class; it
is not conversational authorization for arbitrary actions. Dry-run raw
keyboard, pointer, scroll, or drag actions first when practical:

```bash
linux-computer-use --json --dry-run action press-key --app 'hypr:<address>' --key ctrl+l
linux-computer-use --json approvals grant --app 'hypr:<address>' --scope session
linux-computer-use --json action type-text --app 'hypr:<address>' --text "hello"
```

CLI element actions can use the stored state ID plus either the legacy element
ID or the numeric Sky index:

```bash
linux-computer-use --json action click --app 'class:<class>' --state-id <state_id> --element-index <index>
linux-computer-use --json action set-value --app 'class:<class>' --state-id <state_id> --element-index <index> --value "text"
linux-computer-use --json action select-text --app 'class:<class>' --state-id <state_id> --element-index <index> --text "target"
```

Do not run live write actions against communication apps, terminals, browsers,
or externally visible apps unless the user explicitly approved that exact
target and action. Use the controlled GTK fixture for manual write checks.

Revoke the approval when the task is complete:

```bash
linux-computer-use --json approvals revoke --app 'class:<exact-class>'
```

Default snapshots live below the user's private runtime/state parents. Avoid
printing raw screenshots or accessibility text unless needed. If `--out` is
required, use a newly created mode-0700 temporary directory and delete it after
review; do not use a shared fixed `/tmp` path for sensitive apps.

## Direct Contract Check

Call MCP-style tools directly from the shell when that is easier than starting the MCP server:

```bash
linux-computer-use --json tool-call list_apps --args-json '{}'
linux-computer-use --json tool-call get_app_state --args-json '{"app":"class:<approved-class>"}'
```

`tool-call` is one process per invocation, so use the MCP server—not separate
shell invocations—for a state-gated action sequence.

For Codex MCP integration, configure:

```toml
[mcp_servers.linux-computer-use]
command = "linux-computer-use"
args = ["mcp"]
startup_timeout_sec = 10
```

This backend controls already-running Hyprland windows only; it does not launch
apps. Chrome/Electron accessibility can be absent even when screenshots work.
If `ydotoold` is inactive, report pointer click/scroll/drag as unavailable while
continuing to use available AT-SPI and `wtype` paths.
